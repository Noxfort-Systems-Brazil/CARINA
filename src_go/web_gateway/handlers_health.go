// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"encoding/json"
	"net/http"
	"time"
)

// HealthHandler provides healthcheck diagnostics and root redirection.
type HealthHandler struct {
	port      int
	isEnabled func() bool
}

// NewHealthHandler creates a new HealthHandler.
func NewHealthHandler(port int, isEnabled func() bool) *HealthHandler {
	return &HealthHandler{port: port, isEnabled: isEnabled}
}

// ServeHealth handles /health status JSON queries.
func (h *HealthHandler) ServeHealth(w http.ResponseWriter, r *http.Request) {
	enabled := false
	if h.isEnabled != nil {
		enabled = h.isEnabled()
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(HealthStatus{
		Status:         "online",
		Service:        "carina-web-gateway-go",
		Port:           h.port,
		GatewayEnabled: enabled,
		Timestamp:      time.Now().Unix(),
	})
}

// ServeRoot redirects "/" to "/cco".
func (h *HealthHandler) ServeRoot(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/" {
		http.Redirect(w, r, "/cco", http.StatusTemporaryRedirect)
		return
	}
	http.NotFound(w, r)
}
