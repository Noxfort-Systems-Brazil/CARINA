// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// EVPHandler handles HTTP transport for ambulance telemetry ingestion (Delivery Layer).
type EVPHandler struct {
	ingestionService TelemetryIngestionService
	port             int
}

// NewEVPHandler creates a new EVP HTTP transport handler.
func NewEVPHandler(service TelemetryIngestionService, port int) *EVPHandler {
	return &EVPHandler{
		ingestionService: service,
		port:             port,
	}
}

// ServeHTTP routes GET diagnostics and POST telemetry ingestion requests.
func (h *EVPHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "online",
			"service": "carina-evp-go-ingestion",
			"port":    h.port,
		})
		return
	}

	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}

	cleanPath := strings.Trim(r.URL.Path, "/")
	pathSegments := strings.Split(cleanPath, "/")
	extractedVehicleID := ""
	if len(pathSegments) > 1 {
		last := pathSegments[len(pathSegments)-1]
		if last != "amb" && last != "telemetry" && last != "" {
			extractedVehicleID = last
		}
	}

	body, err := io.ReadAll(io.LimitReader(r.Body, 1024*64))
	if err != nil {
		http.Error(w, "Bad Request", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	if err := h.ingestionService.Ingest(payload, extractedVehicleID); err != nil {
		http.Error(w, fmt.Sprintf("Ingestion error: %v", err), http.StatusInternalServerError)
		return
	}

	// 204 No Content for ultra-fast vehicle ping ACK
	w.WriteHeader(http.StatusNoContent)
}
