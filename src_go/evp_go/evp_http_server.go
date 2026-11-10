// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

// TelemetryPayload represents the GPS/siren ping sent from emergency vehicles.
type TelemetryPayload struct {
	VehicleID   string  `json:"vehicle_id"`
	Corporation string  `json:"corporation"`
	Latitude    float64 `json:"latitude"`
	Longitude   float64 `json:"longitude"`
	SpeedKmh    float64 `json:"speed_kmh"`
	HeadingDeg  float64 `json:"heading_deg"`
	SirenActive bool    `json:"siren_active"`
	Timestamp   int64   `json:"timestamp,omitempty"`
}

// TelemetryCallback is called when valid telemetry is received.
type TelemetryCallback func(payload TelemetryPayload)

// EVPServer handles incoming vehicle pings with microsecond latency.
type EVPServer struct {
	mu          sync.RWMutex
	port        int
	masterToken string
	server      *http.Server
	callback    TelemetryCallback
	isRunning   bool
}

// NewEVPServer creates a new Go EVP ingestion server.
func NewEVPServer(port int, masterToken string, callback TelemetryCallback) *EVPServer {
	if port <= 0 {
		port = 8085
	}
	return &EVPServer{
		port:        port,
		masterToken: strings.TrimSpace(masterToken),
		callback:    callback,
	}
}

// Start begins listening in background.
func (s *EVPServer) Start() error {
	s.mu.Lock()
	if s.isRunning {
		s.mu.Unlock()
		return nil
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", s.handleRequest)

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", s.port),
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}
	s.isRunning = true
	s.mu.Unlock()

	go func() {
		log.Printf("[EVP-Go] 📡 Servidor de Ingestão EVP ouvindo na porta %d (somente recebimento)...", s.port)
		if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("[EVP-Go] Erro no servidor HTTP: %v", err)
		}
	}()

	return nil
}

// Stop gracefully shuts down the HTTP server.
func (s *EVPServer) Stop(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.isRunning || s.server == nil {
		return nil
	}

	s.isRunning = false
	return s.server.Shutdown(ctx)
}

// handleRequest routes POST pings by vehicle ID and diagnostic GET requests.
func (s *EVPServer) handleRequest(w http.ResponseWriter, r *http.Request) {
	// 1. Health check & Diagnostics
	if r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "online",
			"service": "carina-evp-go-ingestion",
			"port":    s.port,
		})
		return
	}

	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	// 2. Token Security Validation (if masterToken is configured)
	if s.masterToken != "" {
		authHeader := r.Header.Get("Authorization")
		customToken := r.Header.Get("X-EVP-Token")

		tokenReceived := ""
		if strings.HasPrefix(authHeader, "Bearer ") {
			tokenReceived = strings.TrimPrefix(authHeader, "Bearer ")
		} else if customToken != "" {
			tokenReceived = customToken
		}

		if strings.TrimSpace(tokenReceived) != s.masterToken {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
	}

	// 3. Extract Vehicle ID from path (e.g. /v1, /v2, /amb/v1, /samu-01)
	cleanPath := strings.Trim(r.URL.Path, "/")
	pathSegments := strings.Split(cleanPath, "/")

	extractedVehicleID := ""
	if len(pathSegments) > 0 {
		lastSegment := pathSegments[len(pathSegments)-1]
		if lastSegment != "telemetry" && lastSegment != "evp" && lastSegment != "" {
			extractedVehicleID = lastSegment
		}
	}

	// 4. Read body
	body, err := io.ReadAll(io.LimitReader(r.Body, 1024*64))
	if err != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var payload TelemetryPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	if payload.VehicleID == "" && extractedVehicleID != "" {
		payload.VehicleID = extractedVehicleID
	} else if payload.VehicleID == "" {
		payload.VehicleID = "VIATURA_DESCONHECIDA"
	}

	if payload.Timestamp == 0 {
		payload.Timestamp = time.Now().UnixMilli()
	}

	// 5. Fire-and-forget dispatch to callback
	if s.callback != nil {
		go s.callback(payload)
	}

	// 6. Fast 204 No Content response
	w.WriteHeader(http.StatusNoContent)
}
