// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"carina/src_go/evp_go"
	"carina/src_go/pkg/manager"
	"carina/src_go/web_gateway"
)

func resolveFlagOrEnv(flagVal, envKey string) string {
	if trimmed := strings.TrimSpace(flagVal); trimmed != "" {
		return trimmed
	}
	return strings.TrimSpace(os.Getenv(envKey))
}

func resolvePortFlagOrEnv(explicitFlags map[string]bool, flagName string, flagVal int, envKey string) int {
	if explicitFlags[flagName] {
		return flagVal
	}
	if raw := strings.TrimSpace(os.Getenv(envKey)); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil && parsed > 0 && parsed <= 65535 {
			return parsed
		}
	}
	return flagVal
}

func main() {
	trapPort := flag.Int("trap-port", 162, "UDP port for listening to SNMP Traps")
	webPort := flag.Int("web-port", 2201, "HTTP port for Remote Gateway (CCO & EVP)")
	evpPort := flag.Int("evp-port", 8085, "HTTP port for EVP vehicle telemetry ingestion")
	webEnabled := flag.Bool("web-enabled", false, "Initial enabled state for Remote Gateway")
	evpTokenFlag := flag.String("evp-token", "", "Authentication token for EVP HTTP endpoints")
	ccoTokenFlag := flag.String("cco-token", "", "Authentication token for CCO HTTP/SSE endpoints")
	allowedOriginFlag := flag.String("allowed-origin", "", "Allowed CORS origin for CCO endpoints")
	tlsCertFlag := flag.String("tls-cert", "", "Optional TLS certificate file path for HTTP servers")
	tlsKeyFlag := flag.String("tls-key", "", "Optional TLS private key file path for HTTP servers")
	flag.Parse()

	explicitFlags := make(map[string]bool)
	flag.Visit(func(f *flag.Flag) {
		explicitFlags[f.Name] = true
	})

	resolvedTrapPort := resolvePortFlagOrEnv(explicitFlags, "trap-port", *trapPort, "CARINA_TRAP_PORT")
	resolvedWebPort := resolvePortFlagOrEnv(explicitFlags, "web-port", *webPort, "CARINA_GATEWAY_PORT")
	resolvedEVPToken := resolveFlagOrEnv(*evpTokenFlag, "CARINA_EVP_AUTH_TOKEN")
	resolvedCCOToken := resolveFlagOrEnv(*ccoTokenFlag, "CARINA_CCO_AUTH_TOKEN")
	resolvedOrigin := resolveFlagOrEnv(*allowedOriginFlag, "CARINA_CCO_ALLOWED_ORIGIN")
	resolvedCert := resolveFlagOrEnv(*tlsCertFlag, "CARINA_GATEWAY_TLS_CERT")
	resolvedKey := resolveFlagOrEnv(*tlsKeyFlag, "CARINA_GATEWAY_TLS_KEY")

	// Redirect all Go logs to stderr, reserving stdout strictly for NDJSON data
	log.SetOutput(os.Stderr)
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds | log.Lshortfile)

	log.Println("==================================================")
	log.Println("CARINA HARDWARE & WEB GATEWAY (Go Field Edition)")
	log.Println("Control Communication: Pure OS Pipes (stdin/stdout)")
	log.Println("==================================================")

	outWriter := &stdoutWriter{
		writer: bufio.NewWriter(os.Stdout),
	}
	ipcHub := NewIPCHub(outWriter)

	// Instantiate connection manager for traffic controllers
	mgr := manager.NewHardwareManager(resolvedTrapPort, func(event interface{}) {
		ipcHub.Broadcast(event)
	})

	if err := mgr.Start(); err != nil {
		log.Printf("[Gateway Start Error] %v", err)
	}

	// Instantiate and start Web Gateway on resolved port for CCO and EVP
	webGateway := web_gateway.NewWebGatewayServer(resolvedWebPort, func(event interface{}) {
		ipcHub.Broadcast(event)
	})
	webGateway.SetAuthTokens(resolvedEVPToken, resolvedCCOToken)
	if resolvedOrigin != "" {
		webGateway.SetAllowedOrigin(resolvedOrigin)
	}
	if resolvedCert != "" && resolvedKey != "" {
		webGateway.SetTLSConfig(resolvedCert, resolvedKey)
	}
	if *webEnabled {
		webGateway.SetEnabled(true)
	}
	if err := webGateway.Start(); err != nil {
		log.Printf("[WebGateway Start Error] %v", err)
	}

	// Instantiate and start EVP ingestion server on port 8085 for vehicle GPS antennas
	evpServer := evp_go.NewEVPServer(*evpPort, resolvedEVPToken, func(payload evp_go.TelemetryPayload) {
		eventMsg := map[string]interface{}{
			"type":       "event",
			"event_type": "evp_telemetry",
			"payload":    payload,
		}
		ipcHub.Broadcast(eventMsg)
		webGateway.BroadcastCCO(map[string]interface{}{
			"type":    "evp_telemetry",
			"vehicle": payload,
		})
	})
	if resolvedCert != "" && resolvedKey != "" {
		evpServer.SetTLSConfig(resolvedCert, resolvedKey)
	}
	if err := evpServer.Start(); err != nil {
		log.Printf("[EVPServer Start Error] %v", err)
	}

	// Capture OS interrupt and termination signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM, syscall.SIGPIPE)

	go func() {
		sig := <-sigChan
		log.Printf("[Gateway OS Signal] Signal received: %v. Executing shutdown failsafe...", sig)
		mgr.ShutdownAll()
		shutCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		_ = webGateway.Stop(shutCtx)
		_ = evpServer.Stop(shutCtx)
		cancel()
		os.Exit(0)
	}()

	// Main stdin reading loop with bounded command concurrency
	scanner := bufio.NewScanner(os.Stdin)
	buf := make([]byte, 1024*1024)
	scanner.Buffer(buf, len(buf))
	cmdSem := make(chan struct{}, 64)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var req RequestEnvelope
		if err := json.Unmarshal(line, &req); err != nil {
			log.Printf("[Gateway Protocol Error] Error reading JSON: %v (raw: %s)", err, string(line))
			outWriter.Send(ResponseEnvelope{
				ID:      0,
				Type:    "response",
				Success: false,
				Error:   fmt.Sprintf("invalid json: %v", err),
			})
			continue
		}

		// Dispatch concurrently within bounded semaphore to keep stdin reader responsive without unbounded goroutines
		cmdSem <- struct{}{}
		go func(r RequestEnvelope) {
			defer func() { <-cmdSem }()
			handleCommandWithEVP(r, mgr, webGateway, evpServer, outWriter)
		}(req)
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		log.Printf("[Gateway Stdin Error] %v", err)
	}

	// EOF detected: parent Python process terminated or closed pipe
	log.Println("[Gateway Stdin] EOF detected on pipe. Parent process exited. Executing global shutdown...")
	mgr.ShutdownAll()
	shutCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	_ = webGateway.Stop(shutCtx)
	_ = evpServer.Stop(shutCtx)
	cancel()
	log.Println("[Gateway Stdin] Gateway terminated safely.")
}
