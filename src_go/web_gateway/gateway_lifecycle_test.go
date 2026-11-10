// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestTailscaleClientStatusAndFunnel(t *testing.T) {
	mockRunner := func(ctx context.Context, name string, args ...string) ([]byte, error) {
		if len(args) >= 2 && args[0] == "status" && args[1] == "--json" {
			return []byte(`{"BackendState":"Running","CertDomains":["carina-node.tail08aec6.ts.net"],"Self":{"DNSName":"carina-node.tail08aec6.ts.net.","Online":true}}`), nil
		}
		if len(args) >= 3 && args[0] == "funnel" && args[1] == "status" {
			return []byte(`{"AllowFunnel":{"carina-node.tail08aec6.ts.net:443":true}}`), nil
		}
		return []byte(`ok`), nil
	}

	client := NewTailscaleClientWithRunner(mockRunner)
	res := client.GetStatus(context.Background())
	if !res.Success || !res.Running || !res.FunnelActive {
		t.Errorf("expected active Tailscale funnel status, got %+v", res)
	}
	if res.CCOUrl != "https://carina-node.tail08aec6.ts.net/cco" {
		t.Errorf("unexpected CCO URL: %s", res.CCOUrl)
	}
	if res.EVPUrl != "https://carina-node.tail08aec6.ts.net/amb/v1" {
		t.Errorf("unexpected EVP URL: %s", res.EVPUrl)
	}
}

func TestWebGatewayLifecycleAndBroadcast(t *testing.T) {
	srv := NewWebGatewayServer(2201, nil)
	if err := srv.Start(); err != nil {
		t.Fatalf("failed starting gateway server: %v", err)
	}

	// Verify broadcast invocation does not error
	srv.BroadcastCCO(map[string]string{"text": "Lifecycle test"})

	time.Sleep(50 * time.Millisecond)

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := srv.Stop(ctx); err != nil {
		t.Fatalf("failed stopping gateway server: %v", err)
	}
}

func TestWebGatewayRequireEnabledMiddleware(t *testing.T) {
	srv := NewWebGatewayServer(2205, nil)

	handler := srv.requireEnabled(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	// 1. By default, srv.IsEnabled() is false -> must return 503 Service Unavailable
	req := httptest.NewRequest(http.MethodGet, "/amb", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusServiceUnavailable {
		t.Errorf("expected 503 Service Unavailable when disabled, got %d", resp.StatusCode)
	}

	// 2. SetEnabled(true) -> must pass through and return 200 OK
	srv.SetEnabled(true)
	w2 := httptest.NewRecorder()
	handler(w2, req)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusOK {
		t.Errorf("expected 200 OK when enabled, got %d", resp2.StatusCode)
	}

	// 3. SetEnabled(false) again -> must return 503 again
	srv.SetEnabled(false)
	w3 := httptest.NewRecorder()
	handler(w3, req)

	resp3 := w3.Result()
	if resp3.StatusCode != http.StatusServiceUnavailable {
		t.Errorf("expected 503 Service Unavailable after re-disabling, got %d", resp3.StatusCode)
	}
}
