// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// CCOHandler handles HTTP transport for CCO static assets, topology, and SSE streaming (Delivery Layer).
type CCOHandler struct {
	streamingService CCOStreamingService
	distDir          string
	topologyPath     string
}

func findDistDir() string {
	if envDir := os.Getenv("CARINA_CCO_DIST_DIR"); envDir != "" {
		if info, err := os.Stat(envDir); err == nil && info.IsDir() {
			return envDir
		}
	}

	candidates := []string{
		"/opt/carina/ui/dist",
		"src_tsx/dist",
		"../src_tsx/dist",
		"../../src_tsx/dist",
		"src_cco/dist",
		"../src_cco/dist",
		"../../src_cco/dist",
	}
	for _, c := range candidates {
		if info, err := os.Stat(c); err == nil && info.IsDir() {
			return c
		}
	}
	return "src_tsx/dist"
}

func findTopologyPath() string {
	if envPath := os.Getenv("CARINA_TOPOLOGY_PATH"); envPath != "" {
		if info, err := os.Stat(envPath); err == nil && !info.IsDir() {
			return envPath
		}
	}

	var candidates []string

	// Dynamic resolution of user Documents directory across locales (Linux/macOS)
	if home, err := os.UserHomeDir(); err == nil && home != "" {
		candidates = append(candidates,
			filepath.Join(home, "Documents", "Carina", "results", "hft_live_session", "maps", "map_topology.json"),
			filepath.Join(home, "Documentos", "Carina", "results", "hft_live_session", "maps", "map_topology.json"),
		)
	}

	candidates = append(candidates,
		"/opt/carina/results/hft_live_session/maps/map_topology.json",
		"results/hft_live_session/maps/map_topology.json",
		"../results/hft_live_session/maps/map_topology.json",
		"../../results/hft_live_session/maps/map_topology.json",
	)

	for _, c := range candidates {
		if info, err := os.Stat(c); err == nil && !info.IsDir() {
			return c
		}
	}
	return candidates[0]
}

// NewCCOHandler creates a new CCO HTTP transport handler.
func NewCCOHandler(streaming CCOStreamingService) *CCOHandler {
	return &CCOHandler{
		streamingService: streaming,
		distDir:          findDistDir(),
		topologyPath:     findTopologyPath(),
	}
}

// SetDistDir allows overriding the static build directory (useful for tests).
func (h *CCOHandler) SetDistDir(dir string) {
	h.distDir = dir
}

// SetTopologyPath allows overriding the map topology file path (useful for tests).
func (h *CCOHandler) SetTopologyPath(path string) {
	h.topologyPath = path
}

// ServeTopology serves the JSON vector topology representing road network and traffic light nodes.
func (h *CCOHandler) ServeTopology(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	target := h.topologyPath
	data, err := os.ReadFile(target)
	if err != nil {
		target = findTopologyPath()
		data, err = os.ReadFile(target)
		if err != nil {
			http.Error(w, `{"error":"map_topology.json not found"}`, http.StatusNotFound)
			return
		}
	}

	_, _ = w.Write(data)
}

// ServePage serves static frontend assets (HTML, JS, CSS) with SPA index.html fallback.
func (h *CCOHandler) ServePage(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/cco/stream" {
		h.ServeStream(w, r)
		return
	}
	if r.URL.Path == "/cco/topology" {
		h.ServeTopology(w, r)
		return
	}
	if r.URL.Path == "/cco/broadcast" {
		h.ServeBroadcast(w, r)
		return
	}

	dist := h.distDir
	if info, err := os.Stat(dist); err != nil || !info.IsDir() {
		dist = findDistDir()
	}

	// Normalize subpath after /cco
	relPath := strings.TrimPrefix(r.URL.Path, "/cco")
	relPath = strings.TrimPrefix(relPath, "/")
	if relPath == "" {
		relPath = "index.html"
	}

	targetFile := filepath.Join(dist, relPath)
	info, err := os.Stat(targetFile)
	if err == nil && !info.IsDir() {
		if strings.HasPrefix(relPath, "assets/") {
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
		} else if relPath == "index.html" {
			w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
			w.Header().Set("Pragma", "no-cache")
			w.Header().Set("Expires", "0")
		}
		http.ServeFile(w, r, targetFile)
		return
	}

	// Never return index.html for missing static assets (prevent SyntaxError: Unexpected token '<' in JS)
	if strings.HasPrefix(relPath, "assets/") || strings.Contains(relPath, ".") {
		http.NotFound(w, r)
		return
	}

	// SPA fallback: return index.html for client-side routing
	indexPath := filepath.Join(dist, "index.html")
	if _, err := os.Stat(indexPath); err == nil {
		w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
		http.ServeFile(w, r, indexPath)
		return
	}

	// Standalone fallback before frontend build is executed
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`<!DOCTYPE html><html><head><title>CARINA CCO</title></head><body style="background:#020617;color:#f8fafc;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;"><h1>CARINA CCO Videowall - Aguardando compilação do frontend</h1></body></html>`))
}

// ServeStream handles Server-Sent Events (SSE) connections for live videowalls.
func (h *CCOHandler) ServeStream(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported!", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache, no-transform")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	clientChan := make(chan []byte, 32)
	h.streamingService.RegisterClient(clientChan)
	defer h.streamingService.UnregisterClient(clientChan)

	// Send initial connection handshake event
	initMsg := []byte("data: {\"type\":\"connected\",\"message\":\"Conectado ao CARINA CCO Gateway (Go)\"}\n\n")
	_, _ = w.Write(initMsg)
	flusher.Flush()

	// Keep-Alive Heartbeat ticker (15s) to prevent intermediate proxies/NAT from dropping idle connections
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	notify := r.Context().Done()
	for {
		select {
		case <-notify:
			return
		case <-ticker.C:
			// Send SSE comment heartbeat to maintain TCP keep-alive without triggering client payload events
			_, _ = w.Write([]byte(": keepalive\n\n"))
			flusher.Flush()
		case msg, ok := <-clientChan:
			if !ok {
				return
			}
			_, _ = w.Write(msg)
			flusher.Flush()
		}
	}
}

// ServeBroadcast handles HTTP POST ingestion of CCO telemetry packets from any CARINA process.
func (h *CCOHandler) ServeBroadcast(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if r.Method == http.MethodOptions {
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"Method not allowed, use POST"}`, http.StatusMethodNotAllowed)
		return
	}

	// Short-circuit: If no clients are connected to the CCO videowall/stream,
	// acknowledge immediately to prevent unnecessary CPU, memory allocation, and JSON parsing.
	if h.streamingService.ClientCount() == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"success":true,"clients":0}`))
		return
	}

	body, err := io.ReadAll(io.LimitReader(r.Body, 5*1024*1024))
	if err != nil {
		http.Error(w, `{"error":"Failed to read request body"}`, http.StatusBadRequest)
		return
	}

	var payload interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		http.Error(w, `{"error":"Invalid JSON payload"}`, http.StatusBadRequest)
		return
	}

	_ = h.streamingService.Broadcast(payload)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"success":true}`))
}
