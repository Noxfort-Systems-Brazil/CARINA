// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

func TestEVPServer_HealthCheck(t *testing.T) {
	server := NewEVPServer(8085, "secret-token", nil)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	server.handleRequest(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Esperado status 200, recebido %d", w.Code)
	}
}

func TestEVPServer_TelemetryWithToken(t *testing.T) {
	var receivedPayload TelemetryPayload
	var wg sync.WaitGroup
	wg.Add(1)

	server := NewEVPServer(8085, "token-12345", func(p TelemetryPayload) {
		receivedPayload = p
		wg.Done()
	})

	body := []byte(`{"latitude": -23.55, "longitude": -46.63, "speed_kmh": 70.0, "siren_active": true}`)
	req := httptest.NewRequest(http.MethodPost, "/v1", bytes.NewBuffer(body))
	req.Header.Set("Authorization", "Bearer token-12345")
	w := httptest.NewRecorder()

	server.handleRequest(w, req)

	if w.Code != http.StatusNoContent {
		t.Fatalf("Esperado status 204, recebido %d", w.Code)
	}

	wg.Wait()

	if receivedPayload.VehicleID != "v1" {
		t.Errorf("Esperado vehicle_id 'v1', recebido '%s'", receivedPayload.VehicleID)
	}
	if !receivedPayload.SirenActive {
		t.Errorf("Esperado siren_active true")
	}
}

func TestEVPServer_UnauthorizedWithoutToken(t *testing.T) {
	server := NewEVPServer(8085, "token-segredo-forte", nil)

	body := []byte(`{"latitude": -23.55, "longitude": -46.63}`)
	req := httptest.NewRequest(http.MethodPost, "/v2", bytes.NewBuffer(body))
	// No authorization header
	w := httptest.NewRecorder()

	server.handleRequest(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("Esperado status 401 Unauthorized, recebido %d", w.Code)
	}
}

func TestEVPServer_StartAndStop(t *testing.T) {
	server := NewEVPServer(18085, "", nil)
	if err := server.Start(); err != nil {
		t.Fatalf("Falha ao iniciar servidor: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := server.Stop(ctx); err != nil {
		t.Fatalf("Falha ao parar servidor: %v", err)
	}
}
