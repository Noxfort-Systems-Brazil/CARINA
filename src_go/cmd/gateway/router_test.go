// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.

// File: src_go/cmd/gateway/router_test.go
// Author: Gabriel Moraes
// Date: September 2026

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"carina/src_go/pkg/manager"
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

	handleCommand(req, mgr, out)

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

	handleCommand(req, mgr, out)

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
	}, mgr, out)
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
	}, mgr, out)
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
	}, mgr, out)
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
	}, mgr, out)
	resp = readLastResponse(t, buf)
	if resp.Success {
		t.Errorf("expected decision to fail for disconnected intersection")
	}

	// Get telemetry for disconnected intersection returns offline telemetry
	handleCommand(RequestEnvelope{
		ID:             205,
		Cmd:            "get_telemetry",
		IntersectionID: "tl_none",
	}, mgr, out)
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
	}, mgr, out)
	resp = readLastResponse(t, buf)
	if !resp.Success {
		t.Errorf("expected emergency release to succeed")
	}
}
