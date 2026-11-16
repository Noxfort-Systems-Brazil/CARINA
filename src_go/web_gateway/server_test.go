// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestCleanDomain(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"carina.tail08aec6.ts.net", "carina.tail08aec6.ts.net"},
		{"carina.tail08aec6.ts.net.", "carina.tail08aec6.ts.net"},
		{"https://carina.tail08aec6.ts.net/", "carina.tail08aec6.ts.net"},
		{"  my-node.tail1234.ts.net.  ", "my-node.tail1234.ts.net"},
	}

	for _, c := range cases {
		got := CleanDomain(c.input)
		if got != c.expected {
			t.Errorf("CleanDomain(%q) = %q, expected %q", c.input, got, c.expected)
		}
	}
}

func TestHealthHandler(t *testing.T) {
	handler := NewHealthHandler(2201, func() bool { return true })
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	handler.ServeHealth(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", resp.StatusCode)
	}

	var data HealthStatus
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		t.Fatalf("failed decoding health JSON: %v", err)
	}

	if data.Service != "carina-web-gateway-go" || data.Port != 2201 || !data.GatewayEnabled {
		t.Errorf("unexpected health status payload: %+v", data)
	}
}

func TestHealthHandlerRootRedirect(t *testing.T) {
	handler := NewHealthHandler(2201, func() bool { return false })
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	w := httptest.NewRecorder()

	handler.ServeRoot(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusTemporaryRedirect {
		t.Errorf("expected 307 Redirect, got %d", resp.StatusCode)
	}
	if loc := resp.Header.Get("Location"); loc != "/cco" {
		t.Errorf("expected redirect to /cco, got %s", loc)
	}
}

func TestEVPHandlerAndIngestionUseCase(t *testing.T) {
	var capturedEvent interface{}
	dispatcher := FuncEventDispatcher(func(evt interface{}) {
		capturedEvent = evt
	})

	ingestor := NewEVPIngestionUseCase(dispatcher)
	handler := NewEVPHandler(ingestor, 2201)

	// 1. Diagnostics GET
	getReq := httptest.NewRequest(http.MethodGet, "/amb", nil)
	getW := httptest.NewRecorder()
	handler.ServeHTTP(getW, getReq)
	if getW.Result().StatusCode != http.StatusOK {
		t.Errorf("expected 200 on GET, got %d", getW.Result().StatusCode)
	}

	// 2. Ingestion POST
	body := []byte(`{"vehicle_id":"SAMU-01","corporation":"SAMU","latitude":-23.55,"longitude":-46.63,"speed_kmh":65.0,"heading_deg":180.0,"siren_active":true}`)
	req := httptest.NewRequest(http.MethodPost, "/amb/v1", bytes.NewReader(body))
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("expected 204 No Content, got %d", resp.StatusCode)
	}

	if capturedEvent == nil {
		t.Fatal("expected captured event to be dispatched, got nil")
	}

	pushEvt, ok := capturedEvent.(EVPPushEvent)
	if !ok {
		t.Fatalf("expected EVPPushEvent type, got %T", capturedEvent)
	}

	if pushEvt.EventType != "evp_telemetry" {
		t.Errorf("expected event_type 'evp_telemetry', got %s", pushEvt.EventType)
	}

	if pushEvt.Payload["vehicle_id"] != "SAMU-01" {
		t.Errorf("expected vehicle_id 'SAMU-01', got %v", pushEvt.Payload["vehicle_id"])
	}
}

func TestCCOHandlerServePageAndTopology(t *testing.T) {
	hub := NewSSEHub()
	ccoService := NewCCOBroadcastUseCase(hub)
	handler := NewCCOHandler(ccoService)

	// 1. Test delivery of /cco page (fallback or index)
	req := httptest.NewRequest(http.MethodGet, "/cco", nil)
	w := httptest.NewRecorder()
	handler.ServePage(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", resp.StatusCode)
	}

	// 2. Test /cco/topology endpoint
	reqTop := httptest.NewRequest(http.MethodGet, "/cco/topology", nil)
	wTop := httptest.NewRecorder()
	handler.ServeTopology(wTop, reqTop)

	respTop := wTop.Result()
	if respTop.Header.Get("Content-Type") != "application/json" {
		t.Errorf("expected application/json, got %s", respTop.Header.Get("Content-Type"))
	}
}

func TestSSEHubAndBroadcastUseCase(t *testing.T) {
	hub := NewSSEHub()
	ccoService := NewCCOBroadcastUseCase(hub)

	clientChan := make(chan []byte, 4)
	hub.AddClient(clientChan)
	if hub.ClientCount() != 1 {
		t.Errorf("expected 1 client, got %d", hub.ClientCount())
	}

	err := ccoService.Broadcast(map[string]string{"text": "Teste Broadcast"})
	if err != nil {
		t.Fatalf("unexpected broadcast error: %v", err)
	}

	select {
	case msg := <-clientChan:
		if !strings.Contains(string(msg), "Teste Broadcast") {
			t.Errorf("unexpected SSE message content: %s", string(msg))
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("timed out waiting for SSE broadcast")
	}

	hub.RemoveClient(clientChan)
	if hub.ClientCount() != 0 {
		t.Errorf("expected 0 clients after removal, got %d", hub.ClientCount())
	}
}

func TestServeBroadcastShortCircuit(t *testing.T) {
	hub := NewSSEHub()
	ccoService := NewCCOBroadcastUseCase(hub)
	handler := NewCCOHandler(ccoService)

	// 1. With 0 clients: should short-circuit and respond fast without parsing
	reqZero := httptest.NewRequest(http.MethodPost, "/cco/broadcast", strings.NewReader(`{"dummy":"payload"}`))
	reqZero.Header.Set("Content-Type", "application/json")
	wZero := httptest.NewRecorder()
	handler.ServeBroadcast(wZero, reqZero)

	respZero := wZero.Result()
	if respZero.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK for short-circuit, got %d", respZero.StatusCode)
	}

	bodyZero, _ := io.ReadAll(respZero.Body)
	if !strings.Contains(string(bodyZero), `"clients":0`) {
		t.Errorf("expected clients:0 in short-circuit response, got %s", string(bodyZero))
	}

	// 2. With 1 client connected: should broadcast
	clientCh := make(chan []byte, 4)
	hub.AddClient(clientCh)
	defer hub.RemoveClient(clientCh)

	reqClient := httptest.NewRequest(http.MethodPost, "/cco/broadcast", strings.NewReader(`{"type":"congestion_update","value":42}`))
	reqClient.Header.Set("Content-Type", "application/json")
	wClient := httptest.NewRecorder()
	handler.ServeBroadcast(wClient, reqClient)

	respClient := wClient.Result()
	if respClient.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK, got %d", respClient.StatusCode)
	}

	select {
	case msg := <-clientCh:
		if !strings.Contains(string(msg), `"value":42`) {
			t.Errorf("expected broadcast message to contain value:42, got %s", string(msg))
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("timed out waiting for broadcast message")
	}
}

func TestWebGatewayAuthAndEnabledGuards(t *testing.T) {
	srv := NewWebGatewayServer(2201, nil)
	srv.SetAuthTokens("evp-tok", "cco-tok")
	srv.SetAllowedOrigin("https://cco.carina.local")
	mux := srv.buildMux()

	// 1. When disabled, /amb/v1 must return 503 (never stay exposed)
	reqDisabled := httptest.NewRequest(http.MethodPost, "/amb/v1", strings.NewReader(`{"latitude":-23.5,"longitude":-46.6}`))
	reqDisabled.Header.Set("Authorization", "Bearer evp-tok")
	wDisabled := httptest.NewRecorder()
	mux.ServeHTTP(wDisabled, reqDisabled)
	if wDisabled.Result().StatusCode != http.StatusServiceUnavailable {
		t.Fatalf("expected 503 for /amb/v1 when gateway disabled, got %d", wDisabled.Result().StatusCode)
	}

	// 2. When enabled, /amb/v1 without valid token must return 401
	srv.SetEnabled(true)
	reqNoTok := httptest.NewRequest(http.MethodPost, "/amb/v1", strings.NewReader(`{"latitude":-23.5,"longitude":-46.6}`))
	wNoTok := httptest.NewRecorder()
	mux.ServeHTTP(wNoTok, reqNoTok)
	if wNoTok.Result().StatusCode != http.StatusUnauthorized {
		t.Fatalf("expected 401 for /amb/v1 without token, got %d", wNoTok.Result().StatusCode)
	}

	// 3. With valid EVP token, /amb/v1 succeeds with 204
	reqValidEvp := httptest.NewRequest(http.MethodPost, "/amb/v1", strings.NewReader(`{"latitude":-23.5,"longitude":-46.6}`))
	reqValidEvp.Header.Set("Authorization", "Bearer evp-tok")
	wValidEvp := httptest.NewRecorder()
	mux.ServeHTTP(wValidEvp, reqValidEvp)
	if wValidEvp.Result().StatusCode != http.StatusNoContent {
		t.Fatalf("expected 204 for /amb/v1 with valid token, got %d", wValidEvp.Result().StatusCode)
	}

	// 4. /cco/broadcast enforces CCO token and emits configured CORS origin
	reqCcoBad := httptest.NewRequest(http.MethodPost, "/cco/broadcast", strings.NewReader(`{"ok":true}`))
	wCcoBad := httptest.NewRecorder()
	mux.ServeHTTP(wCcoBad, reqCcoBad)
	if wCcoBad.Result().StatusCode != http.StatusUnauthorized {
		t.Fatalf("expected 401 for /cco/broadcast without token, got %d", wCcoBad.Result().StatusCode)
	}

	reqCcoGood := httptest.NewRequest(http.MethodPost, "/cco/broadcast", strings.NewReader(`{"ok":true}`))
	reqCcoGood.Header.Set("X-CCO-Token", "cco-tok")
	wCcoGood := httptest.NewRecorder()
	mux.ServeHTTP(wCcoGood, reqCcoGood)
	if wCcoGood.Result().StatusCode != http.StatusOK {
		t.Fatalf("expected 200 for /cco/broadcast with valid token, got %d", wCcoGood.Result().StatusCode)
	}
	if origin := wCcoGood.Result().Header.Get("Access-Control-Allow-Origin"); origin != "https://cco.carina.local" {
		t.Errorf("expected custom CORS origin, got %q", origin)
	}
}
