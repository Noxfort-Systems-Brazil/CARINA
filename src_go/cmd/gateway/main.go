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
	"syscall"
	"time"

	"carina/src_go/evp_go"
	"carina/src_go/pkg/manager"
	"carina/src_go/web_gateway"
)

func main() {
	trapPort := flag.Int("trap-port", 162, "UDP port for listening to SNMP Traps")
	webPort := flag.Int("web-port", 2201, "HTTP port for Remote Gateway (CCO & EVP)")
	evpPort := flag.Int("evp-port", 8085, "HTTP port for EVP vehicle telemetry ingestion")
	webEnabled := flag.Bool("web-enabled", false, "Initial enabled state for Remote Gateway")
	flag.Parse()

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
	mgr := manager.NewHardwareManager(*trapPort, func(event interface{}) {
		ipcHub.Broadcast(event)
	})

	if err := mgr.Start(); err != nil {
		log.Printf("[Gateway Start Error] %v", err)
	}

	// Instantiate and start Web Gateway on port 2201 for CCO and EVP
	webGateway := web_gateway.NewWebGatewayServer(*webPort, func(event interface{}) {
		ipcHub.Broadcast(event)
	})
	if *webEnabled {
		webGateway.SetEnabled(true)
	}
	if err := webGateway.Start(); err != nil {
		log.Printf("[WebGateway Start Error] %v", err)
	}

	// Instantiate and start EVP ingestion server on port 8085 for vehicle GPS antennas
	evpServer := evp_go.NewEVPServer(*evpPort, "", func(payload evp_go.TelemetryPayload) {
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
	if err := evpServer.Start(); err != nil {
		log.Printf("[EVPServer Start Error] %v", err)
	}

	// Capture OS interrupt and termination signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM, syscall.SIGPIPE)

	go func() {
		sig := <-sigChan
		log.Printf("[Gateway OS Signal] Signal received: %v. Executing emergency failsafe...", sig)
		mgr.EmergencyReleaseControlAll()
		shutCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		_ = webGateway.Stop(shutCtx)
		_ = evpServer.Stop(shutCtx)
		cancel()
		os.Exit(0)
	}()

	// Main stdin reading loop
	scanner := bufio.NewScanner(os.Stdin)
	buf := make([]byte, 1024*1024)
	scanner.Buffer(buf, len(buf))

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

		// Dispatch concurrently in goroutine to keep stdin reader unblocked
		go handleCommand(req, mgr, webGateway, outWriter)
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		log.Printf("[Gateway Stdin Error] %v", err)
	}

	// EOF detected: parent Python process terminated or closed pipe
	log.Println("[Gateway Stdin] EOF detected on pipe. Parent process exited. Executing global failsafe...")
	mgr.EmergencyReleaseControlAll()
	shutCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	_ = webGateway.Stop(shutCtx)
	_ = evpServer.Stop(shutCtx)
	cancel()
	log.Println("[Gateway Stdin] Gateway terminated safely.")
}
