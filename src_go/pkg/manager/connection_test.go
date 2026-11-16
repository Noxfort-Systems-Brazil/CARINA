// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package manager

import (
	"testing"

	"carina/src_go/pkg/heartbeat"
	"carina/src_go/pkg/protocol"
)

type mockDriver struct {
	released          bool
	shutdown          bool
	lastActionData    map[string]interface{}
	lastLogicalAction int
	lastDecision      string
	telemetryCalls    int
}

func (m *mockDriver) GetProtocolName() string { return "MOCK" }
func (m *mockDriver) ApplyAction(actionData map[string]interface{}) (bool, error) {
	m.lastActionData = actionData
	return true, nil
}
func (m *mockDriver) ApplyLogicalAction(action int, c int, g []int, sc map[int]string) (bool, error) {
	m.lastLogicalAction = action
	return true, nil
}
func (m *mockDriver) ApplyDecision(action string) (bool, error) {
	m.lastDecision = action
	return true, nil
}
func (m *mockDriver) GetTelemetry() (map[string]interface{}, error) {
	m.telemetryCalls++
	return map[string]interface{}{"status": "online"}, nil
}
func (m *mockDriver) SendHeartbeatPulse() (bool, error)         { return true, nil }
func (m *mockDriver) ReleaseControl() (bool, error)             { m.released = true; return true, nil }
func (m *mockDriver) GetBrand() string                          { return "MockBrand" }
func (m *mockDriver) GetModel() string                          { return "MockModel" }
func (m *mockDriver) GetSysDescr() string                       { return "MockDescr" }
func (m *mockDriver) SetMetadata(brand, model, sysDescr string) {}
func (m *mockDriver) Shutdown()                                 { m.shutdown = true }

func TestDisconnectWithExactAndAlternateID(t *testing.T) {
	mgr := &HardwareManager{
		drivers:          make(map[string]protocol.TrafficDriver),
		heartbeats:       make(map[string]*heartbeat.Manager),
		ipToIntersection: make(map[string]string),
	}

	driver := &mockDriver{}
	mgr.drivers["tl_J1"] = driver
	mgr.ipToIntersection["192.168.1.100"] = "tl_J1"

	// Disconnecting with "J1" should resolve to "tl_J1"
	err := mgr.Disconnect("J1")
	if err != nil {
		t.Fatalf("Expected Disconnect to succeed with alternate ID, got: %v", err)
	}

	if !driver.released {
		t.Errorf("Expected driver.ReleaseControl() to have been called")
	}
	if !driver.shutdown {
		t.Errorf("Expected driver.Shutdown() to have been called")
	}
	if _, ok := mgr.drivers["tl_J1"]; ok {
		t.Errorf("Expected driver tl_J1 to be removed from mgr.drivers")
	}
	if _, ok := mgr.ipToIntersection["192.168.1.100"]; ok {
		t.Errorf("Expected IP 192.168.1.100 to be removed from mgr.ipToIntersection")
	}

	// Disconnecting again should return error
	err = mgr.Disconnect("J1")
	if err == nil {
		t.Errorf("Expected error when disconnecting already disconnected intersection")
	}
}

func TestPrefixFallbackOnControlAndTelemetry(t *testing.T) {
	mgr := &HardwareManager{
		drivers:          make(map[string]protocol.TrafficDriver),
		heartbeats:       make(map[string]*heartbeat.Manager),
		ipToIntersection: make(map[string]string),
	}

	dPrefixed := &mockDriver{}
	dBare := &mockDriver{}
	mgr.drivers["tl_J1"] = dPrefixed
	mgr.drivers["J2"] = dBare

	ok, err := mgr.ApplyAction("J1", map[string]interface{}{"action_type": "hold", "stage": 1})
	if err != nil || !ok || dPrefixed.lastActionData["action_type"] != "hold" {
		t.Fatalf("Expected ApplyAction with stripped ID to resolve tl_J1, got ok=%v err=%v", ok, err)
	}

	ok, err = mgr.ApplyLogicalAction("tl_J2", 0, 2, []int{0, 2}, map[int]string{0: "GGrr", 2: "rrGG"})
	if err != nil || !ok || dBare.lastLogicalAction != 0 {
		t.Fatalf("Expected ApplyLogicalAction with tl_ prefix to resolve J2, got ok=%v err=%v", ok, err)
	}

	ok, err = mgr.ApplyDecision("J1", "HOLD")
	if err != nil || !ok || dPrefixed.lastDecision != "HOLD" {
		t.Fatalf("Expected ApplyDecision to resolve tl_J1, got ok=%v err=%v", ok, err)
	}

	tel, err := mgr.GetTelemetry("tl_J2")
	if err != nil || dBare.telemetryCalls != 1 || tel["status"] != "online" {
		t.Fatalf("Expected GetTelemetry to resolve J2, got tel=%v err=%v", tel, err)
	}
}
