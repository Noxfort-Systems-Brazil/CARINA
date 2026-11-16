// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"carina/src_go/evp_go"
	"carina/src_go/pkg/manager"
	"carina/src_go/web_gateway"
)

func newTestStdoutWriter() (*stdoutWriter, *bytes.Buffer) {
	buf := &bytes.Buffer{}
	writer := &stdoutWriter{
		writer: bufio.NewWriter(buf),
	}
	return writer, buf
}

func readLastResponse(t *testing.T, buf *bytes.Buffer) ResponseEnvelope {
	t.Helper()
	lines := strings.Split(strings.TrimSpace(buf.String()), "\n")
	if len(lines) == 0 || lines[len(lines)-1] == "" {
		t.Fatalf("no response written in buffer")
	}
	var resp ResponseEnvelope
	err := json.Unmarshal([]byte(lines[len(lines)-1]), &resp)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	return resp
}

func TestRouterPing(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)

	req := RequestEnvelope{
		ID:  101,
		Cmd: "ping",
	}

	handleCommand(req, mgr, nil, out)

	resp := readLastResponse(t, buf)
	if resp.ID != 101 {
		t.Errorf("expected ID 101, got %d", resp.ID)
	}
	if !resp.Success {
		t.Errorf("expected Success true, got false")
	}
	if resp.Data != "pong" {
		t.Errorf("expected Data 'pong', got %v", resp.Data)
	}
}

func TestRouterUnknownCommand(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)

	req := RequestEnvelope{
		ID:  102,
		Cmd: "non_existent_command",
	}

	handleCommand(req, mgr, nil, out)

	resp := readLastResponse(t, buf)
	if resp.ID != 102 {
		t.Errorf("expected ID 102, got %d", resp.ID)
	}
	if resp.Success {
		t.Errorf("expected Success false, got true")
	}
	if !strings.Contains(resp.Error, "unknown command: non_existent_command") {
		t.Errorf("expected unknown command error, got: %s", resp.Error)
	}
}

func TestRouterDisconnectedOperations(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)

	// Disconnecting an unknown intersection returns an error
	handleCommand(RequestEnvelope{
		ID:             201,
		Cmd:            "disconnect",
		IntersectionID: "unknown_id",
	}, mgr, nil, out)
	resp := readLastResponse(t, buf)
	if resp.ID != 201 || resp.Success {
		t.Errorf("expected failure when disconnecting non-existent intersection, got: %+v", resp)
	}
	if !strings.Contains(resp.Error, "is not connected") {
		t.Errorf("expected 'is not connected' in error, got: %s", resp.Error)
	}

	// Apply action on disconnected intersection should fail
	handleCommand(RequestEnvelope{
		ID:             202,
		Cmd:            "apply_action",
		IntersectionID: "tl_none",
		ActionData:     map[string]interface{}{"stage": 1},
	}, mgr, nil, out)
	resp = readLastResponse(t, buf)
	if resp.Success {
		t.Errorf("expected apply_action to fail for disconnected intersection")
	}
	if !strings.Contains(resp.Error, "disconnected") {
		t.Errorf("expected 'disconnected' in error, got: %s", resp.Error)
	}

	// Apply logical action on disconnected intersection should fail
	handleCommand(RequestEnvelope{
		ID:              203,
		Cmd:             "apply_logical_action",
		IntersectionID:  "tl_none",
		Action:          1,
		CurrentStageIdx: 0,
	}, mgr, nil, out)
	resp = readLastResponse(t, buf)
	if resp.Success {
		t.Errorf("expected apply_logical_action to fail for disconnected intersection")
	}

	// Apply decision on disconnected intersection should fail
	handleCommand(RequestEnvelope{
		ID:             204,
		Cmd:            "decision",
		IntersectionID: "tl_none",
		Decision:       "ADVANCE",
	}, mgr, nil, out)
	resp = readLastResponse(t, buf)
	if resp.Success {
		t.Errorf("expected decision to fail for disconnected intersection")
	}

	// Get telemetry for disconnected intersection returns offline telemetry
	handleCommand(RequestEnvelope{
		ID:             205,
		Cmd:            "get_telemetry",
		IntersectionID: "tl_none",
	}, mgr, nil, out)
	resp = readLastResponse(t, buf)
	if !resp.Success {
		t.Errorf("expected telemetry call to succeed even if offline")
	}
	telem, ok := resp.Telemetry.(map[string]interface{})
	if !ok || telem["status"] != "offline" {
		t.Errorf("expected offline status telemetry, got: %+v", telem)
	}

	// Emergency release all
	handleCommand(RequestEnvelope{
		ID:  206,
		Cmd: "emergency_release",
	}, mgr, nil, out)
	resp = readLastResponse(t, buf)
	if !resp.Success {
		t.Errorf("expected emergency release to succeed")
	}
}

func TestRouterCCOBroadcastAndTailscale(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)

	// Test CCO Broadcast command
	handleCommand(RequestEnvelope{
		ID:   301,
		Cmd:  "cco_broadcast",
		Data: map[string]interface{}{"subtitle": "Teste CCO", "category": "INFO"},
	}, mgr, nil, out)

	resp := readLastResponse(t, buf)
	if resp.ID != 301 || !resp.Success {
		t.Errorf("expected cco_broadcast to succeed, got %+v", resp)
	}

	// Test Tailscale status query
	handleCommand(RequestEnvelope{
		ID:  302,
		Cmd: "tailscale_status",
	}, mgr, nil, out)

	resp = readLastResponse(t, buf)
	if resp.ID != 302 {
		t.Errorf("expected response ID 302 for tailscale_status, got %+v", resp)
	}
}

func TestRouterGatewayEnableAndStatus(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)
	webSrv := web_gateway.NewWebGatewayServer(2209, nil)

	// 1. Initial status -> disabled
	handleCommand(RequestEnvelope{
		ID:  401,
		Cmd: "gateway_get_status",
	}, mgr, webSrv, out)

	resp := readLastResponse(t, buf)
	if resp.ID != 401 || !resp.Success {
		t.Fatalf("expected gateway_get_status success, got %+v", resp)
	}
	data, ok := resp.Data.(map[string]interface{})
	if !ok || data["enabled"] != false {
		t.Errorf("expected gateway to be initially disabled, got %+v", data)
	}

	// 2. Enable gateway
	enabled := true
	handleCommand(RequestEnvelope{
		ID:      402,
		Cmd:     "gateway_set_enabled",
		Enabled: &enabled,
	}, mgr, webSrv, out)

	resp = readLastResponse(t, buf)
	if resp.ID != 402 || !resp.Success {
		t.Fatalf("expected gateway_set_enabled success, got %+v", resp)
	}
	data, ok = resp.Data.(map[string]interface{})
	if !ok || data["enabled"] != true {
		t.Errorf("expected gateway to be enabled, got %+v", data)
	}

	// 3. Status confirms enabled
	handleCommand(RequestEnvelope{
		ID:  403,
		Cmd: "gateway_get_status",
	}, mgr, webSrv, out)

	resp = readLastResponse(t, buf)
	data, _ = resp.Data.(map[string]interface{})
	if data["enabled"] != true {
		t.Errorf("expected status to confirm enabled, got %+v", data)
	}

	// 4. Disable gateway
	disabled := false
	handleCommand(RequestEnvelope{
		ID:      404,
		Cmd:     "gateway_set_enabled",
		Enabled: &disabled,
	}, mgr, webSrv, out)

	resp = readLastResponse(t, buf)
	data, _ = resp.Data.(map[string]interface{})
	if data["enabled"] != false {
		t.Errorf("expected gateway to be disabled, got %+v", data)
	}
}

func TestRouterGatewaySetAuthTokens(t *testing.T) {
	out, buf := newTestStdoutWriter()
	mgr := manager.NewHardwareManager(0, nil)
	webSrv := web_gateway.NewWebGatewayServer(2212, nil)
	evpSrv := evp_go.NewEVPServer(8092, "", nil)

	handleCommandWithEVP(RequestEnvelope{
		ID:            405,
		Cmd:           "gateway_set_auth_tokens",
		EVPAuthToken:  "evp-runtime-secret",
		CCOAuthToken:  "cco-runtime-secret",
		AllowedOrigin: "https://cco.city.gov",
	}, mgr, webSrv, evpSrv, out)

	resp := readLastResponse(t, buf)
	if !resp.Success {
		t.Fatalf("expected gateway_set_auth_tokens success, got err=%s", resp.Error)
	}
	data, ok := resp.Data.(map[string]interface{})
	if !ok || data["evp_auth_configured"] != true || data["cco_auth_configured"] != true {
		t.Errorf("expected both auth tokens configured, got %+v", data)
	}
}
