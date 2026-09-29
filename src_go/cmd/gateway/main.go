// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.

// File: src_go/cmd/gateway/main.go
// Author: Gabriel Moraes
// Date: September 2026

package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"

	"carina/src_go/pkg/manager"
)

func main() {
	trapPort := flag.Int("trap-port", 162, "UDP port for listening to SNMP Traps")
	flag.Parse()

	// Redirect all Go logs to stderr, reserving stdout strictly for NDJSON data
	log.SetOutput(os.Stderr)
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds | log.Lshortfile)
	log.Println("==================================================")
	log.Println("CARINA HARDWARE GATEWAY (Go High-Performance Field Edition)")
	log.Println("Control Communication: stdin/stdout (NDJSON)")
	log.Println("==================================================")

	outWriter := &stdoutWriter{
		writer: bufio.NewWriter(os.Stdout),
	}

	// Instantiate connection manager
	mgr := manager.NewHardwareManager(*trapPort, func(event interface{}) {
		outWriter.Send(event)
	})

	if err := mgr.Start(); err != nil {
		log.Printf("[Gateway Start Error] %v", err)
	}

	// Capture OS interrupt and termination signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM, syscall.SIGPIPE)

	go func() {
		sig := <-sigChan
		log.Printf("[Gateway OS Signal] Signal received: %v. Executing emergency failsafe...", sig)
		mgr.EmergencyReleaseControlAll()
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
		go handleCommand(req, mgr, outWriter)
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		log.Printf("[Gateway Stdin Error] %v", err)
	}

	// EOF detected: parent Python process terminated or closed pipe
	log.Println("[Gateway Stdin] EOF detected on pipe. Parent process exited. Executing global failsafe...")
	mgr.EmergencyReleaseControlAll()
	log.Println("[Gateway Stdin] Gateway terminated safely.")
}
