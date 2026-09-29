// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Noxfort Systems
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

// File: src_go/pkg/manager/connection_test.go
// Author: Gabriel Moraes
// Date: September 2026

package manager

import (
	"testing"

	"carina/src_go/pkg/heartbeat"
	"carina/src_go/pkg/protocol"
)

type mockDriver struct {
	released bool
	shutdown bool
}

func (m *mockDriver) GetProtocolName() string                                                                    { return "MOCK" }
func (m *mockDriver) ApplyAction(actionData map[string]interface{}) (bool, error)                                { return true, nil }
func (m *mockDriver) ApplyLogicalAction(action int, c int, g []int, sc map[int]string) (bool, error)             { return true, nil }
func (m *mockDriver) ApplyDecision(action string) (bool, error)                                                  { return true, nil }
func (m *mockDriver) GetTelemetry() (map[string]interface{}, error)                                             { return nil, nil }
func (m *mockDriver) SendHeartbeatPulse() (bool, error)                                                          { return true, nil }
func (m *mockDriver) ReleaseControl() (bool, error)                                                              { m.released = true; return true, nil }
func (m *mockDriver) GetBrand() string                                                                           { return "MockBrand" }
func (m *mockDriver) GetModel() string                                                                           { return "MockModel" }
func (m *mockDriver) GetSysDescr() string                                                                        { return "MockDescr" }
func (m *mockDriver) SetMetadata(brand, model, sysDescr string)                                                  {}
func (m *mockDriver) Shutdown()                                                                                  { m.shutdown = true }

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
