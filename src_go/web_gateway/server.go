// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

// FuncEventDispatcher allows using a simple callback function as an EventDispatcher.
type FuncEventDispatcher func(event interface{})

func (f FuncEventDispatcher) Dispatch(event interface{}) {
	if f != nil {
		f(event)
	}
}

// WebGatewayServer orchestrates the HTTP gateway on port 2201 for CCO and EVP.
// Acts as the Composition Root (Clean Architecture / Dependency Injection).
type WebGatewayServer struct {
	mu            sync.RWMutex
	port          int
	server        *http.Server
	sseHub        *SSEHub
	ccoService    CCOStreamingService
	evpService    TelemetryIngestionService
	tsClient      *TailscaleClient
	ccoHandler    *CCOHandler
	evpToken      string
	ccoToken      string
	allowedOrigin string
	tlsCertFile   string
	tlsKeyFile    string
	isRunning     bool
	enabled       bool
}

// NewWebGatewayServer builds a fully-injected WebGatewayServer instance.
func NewWebGatewayServer(port int, onEvent func(event interface{})) *WebGatewayServer {
	if port <= 0 {
		port = 2201
	}

	sseHub := NewSSEHub()
	ccoService := NewCCOBroadcastUseCase(sseHub)
	evpService := NewEVPIngestionUseCase(FuncEventDispatcher(onEvent), ccoService)

	return &WebGatewayServer{
		port:          port,
		sseHub:        sseHub,
		ccoService:    ccoService,
		evpService:    evpService,
		tsClient:      NewTailscaleClient(),
		evpToken:      strings.TrimSpace(os.Getenv("CARINA_EVP_AUTH_TOKEN")),
		ccoToken:      strings.TrimSpace(os.Getenv("CARINA_CCO_AUTH_TOKEN")),
		allowedOrigin: ResolveAllowedOrigin(""),
		tlsCertFile:   strings.TrimSpace(os.Getenv("CARINA_GATEWAY_TLS_CERT")),
		tlsKeyFile:    strings.TrimSpace(os.Getenv("CARINA_GATEWAY_TLS_KEY")),
		enabled:       false,
	}
}

// SetAuthTokens updates EVP and CCO authentication tokens at runtime.
func (s *WebGatewayServer) SetAuthTokens(evpToken, ccoToken string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.evpToken = strings.TrimSpace(evpToken)
	s.ccoToken = strings.TrimSpace(ccoToken)
}

// SetAllowedOrigin updates the CORS allowed origin for CCO HTTP/SSE responses.
func (s *WebGatewayServer) SetAllowedOrigin(origin string) {
	resolved := ResolveAllowedOrigin(origin)
	s.mu.Lock()
	s.allowedOrigin = resolved
	handler := s.ccoHandler
	s.mu.Unlock()
	if handler != nil {
		handler.SetAllowedOrigin(resolved)
	}
}

// SetTLSConfig configures TLS cert/key files used by Start().
func (s *WebGatewayServer) SetTLSConfig(certFile, keyFile string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tlsCertFile = strings.TrimSpace(certFile)
	s.tlsKeyFile = strings.TrimSpace(keyFile)
}

func (s *WebGatewayServer) getEVPToken() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.evpToken
}

func (s *WebGatewayServer) getCCOToken() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.ccoToken
}

func (s *WebGatewayServer) getAllowedOrigin() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.allowedOrigin
}

// Tailscale returns the TailscaleClient instance.
func (s *WebGatewayServer) Tailscale() *TailscaleClient {
	return s.tsClient
}

// Port returns the HTTP port configured for this server.
func (s *WebGatewayServer) Port() int {
	return s.port
}

// SetEnabled toggles whether the remote gateway accepts external traffic (CCO/EVP).
func (s *WebGatewayServer) SetEnabled(enabled bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.enabled = enabled
	log.Printf("[WebGateway-Go] 🛡️ Estado do Acesso Remoto atualizado: enabled=%v", enabled)
}

// IsEnabled checks if the remote gateway is currently accepting external traffic.
func (s *WebGatewayServer) IsEnabled() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.enabled
}

// requireEnabled wraps HTTP handlers to reject traffic when the gateway is disabled.
func (s *WebGatewayServer) requireEnabled(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !s.IsEnabled() {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]interface{}{
				"status":  "disconnected",
				"error":   "Remote Gateway is disabled / disconnected in CARINA_CORE",
				"code":    http.StatusServiceUnavailable,
			})
			return
		}
		next(w, r)
	}
}

func (s *WebGatewayServer) buildMux() *http.ServeMux {
	mux := http.NewServeMux()

	healthHandler := NewHealthHandler(s.port, s.IsEnabled)
	evpHandler := NewEVPHandler(s.evpService, s.port)
	ccoHandler := NewCCOHandler(s.ccoService)
	ccoHandler.SetAllowedOrigin(s.getAllowedOrigin())

	s.mu.Lock()
	s.ccoHandler = ccoHandler
	s.mu.Unlock()

	mux.HandleFunc("/health", healthHandler.ServeHealth)
	mux.HandleFunc("/cco", s.requireEnabled(ccoHandler.ServePage))
	mux.HandleFunc("/cco/", s.requireEnabled(ccoHandler.ServePage))
	mux.HandleFunc("/cco/stream", s.requireEnabled(WrapTokenAuth(s.getCCOToken, true, ccoHandler.ServeStream)))
	mux.HandleFunc("/cco/topology", s.requireEnabled(WrapTokenAuth(s.getCCOToken, false, ccoHandler.ServeTopology)))
	mux.HandleFunc("/cco/broadcast", s.requireEnabled(WrapTokenAuth(s.getCCOToken, false, ccoHandler.ServeBroadcast)))
	evpGuarded := s.requireEnabled(WrapTokenAuth(s.getEVPToken, false, evpHandler.ServeHTTP))
	mux.HandleFunc("/amb", evpGuarded)
	mux.HandleFunc("/amb/", evpGuarded)
	mux.HandleFunc("/api/v1/evp/telemetry", evpGuarded)
	mux.HandleFunc("/", healthHandler.ServeRoot)

	return mux
}

// Start boots up the HTTP server and registers modular handlers.
func (s *WebGatewayServer) Start() error {
	s.mu.Lock()
	if s.isRunning {
		s.mu.Unlock()
		return nil
	}
	certFile := s.tlsCertFile
	keyFile := s.tlsKeyFile
	s.mu.Unlock()

	mux := s.buildMux()

	s.mu.Lock()
	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", s.port),
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 0, // Infinite for persistent SSE streaming
	}
	s.isRunning = true
	s.mu.Unlock()

	go func() {
		log.Printf("[WebGateway-Go] 🌐 Gateway Web CARINA ativo na porta %d (CCO & EVP, tls=%v)...", s.port, certFile != "" && keyFile != "")
		var err error
		if certFile != "" && keyFile != "" {
			err = s.server.ListenAndServeTLS(certFile, keyFile)
		} else {
			err = s.server.ListenAndServe()
		}
		if err != nil && err != http.ErrServerClosed {
			log.Printf("[WebGateway-Go] Erro no servidor HTTP: %v", err)
		}
	}()

	return nil
}

// Stop gracefully shuts down the server.
func (s *WebGatewayServer) Stop(ctx context.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.isRunning || s.server == nil {
		return nil
	}
	s.isRunning = false
	return s.server.Shutdown(ctx)
}

// BroadcastCCO delivers live payload updates to all connected CCO videowall clients.
func (s *WebGatewayServer) BroadcastCCO(payload interface{}) {
	_ = s.ccoService.Broadcast(payload)
}
