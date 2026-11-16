// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
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
	tlsCertFile string
	tlsKeyFile  string
	server      *http.Server
	callback    TelemetryCallback
	isRunning   bool
}

// NewEVPServer creates a new Go EVP ingestion server.
func NewEVPServer(port int, masterToken string, callback TelemetryCallback) *EVPServer {
	if port <= 0 {
		port = 8085
	}
	resolvedToken := strings.TrimSpace(masterToken)
	if resolvedToken == "" {
		resolvedToken = strings.TrimSpace(os.Getenv("CARINA_EVP_AUTH_TOKEN"))
	}
	return &EVPServer{
		port:        port,
		masterToken: resolvedToken,
		tlsCertFile: strings.TrimSpace(os.Getenv("CARINA_GATEWAY_TLS_CERT")),
		tlsKeyFile:  strings.TrimSpace(os.Getenv("CARINA_GATEWAY_TLS_KEY")),
		callback:    callback,
	}
}

// SetMasterToken dynamically updates the bearer/header token expected on POST telemetry calls.
func (s *EVPServer) SetMasterToken(token string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.masterToken = strings.TrimSpace(token)
}

// getMasterToken returns the currently active master token safely.
func (s *EVPServer) getMasterToken() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.masterToken
}

// SetTLSConfig sets optional TLS certificate paths before Start().
func (s *EVPServer) SetTLSConfig(certFile, keyFile string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tlsCertFile = strings.TrimSpace(certFile)
	s.tlsKeyFile = strings.TrimSpace(keyFile)
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
	certFile := s.tlsCertFile
	keyFile := s.tlsKeyFile
	s.isRunning = true
	s.mu.Unlock()

	go func() {
		log.Printf("[EVP-Go] 📡 Servidor de Ingestão EVP ouvindo na porta %d (tls=%v)...", s.port, certFile != "" && keyFile != "")
		var err error
		if certFile != "" && keyFile != "" {
			err = s.server.ListenAndServeTLS(certFile, keyFile)
		} else {
			err = s.server.ListenAndServe()
		}
		if err != nil && err != http.ErrServerClosed {
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
	if expectedToken := s.getMasterToken(); expectedToken != "" {
		authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
		customToken := strings.TrimSpace(r.Header.Get("X-EVP-Token"))

		tokenReceived := ""
		if len(authHeader) > 7 && strings.EqualFold(authHeader[:7], "Bearer ") {
			tokenReceived = strings.TrimSpace(authHeader[7:])
		} else if customToken != "" {
			tokenReceived = customToken
		}

		if subtle.ConstantTimeCompare([]byte(tokenReceived), []byte(expectedToken)) != 1 {
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
