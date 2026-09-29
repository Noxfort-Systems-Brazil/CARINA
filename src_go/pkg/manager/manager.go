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

// File: src_go/pkg/manager/manager.go
// Author: Gabriel Moraes
// Date: September 2026

package manager

import (
	"fmt"
	"log"
	"sync"

	"carina/src_go/pkg/heartbeat"
	"carina/src_go/pkg/protocol"
	"carina/src_go/pkg/traplistener"
)

// HardwareManager orchestrates traffic signal drivers, heartbeats, and the trap listener.
// Delegates connections to connection.go and emergency failsafes to failsafe.go.
type HardwareManager struct {
	mu               sync.RWMutex
	drivers          map[string]protocol.TrafficDriver
	heartbeats       map[string]*heartbeat.Manager
	ipToIntersection map[string]string
	trapListener     *traplistener.Listener
	sendEventFn      func(event interface{})
}

// NewHardwareManager instantiates the primary connection orchestrator.
func NewHardwareManager(trapPort int, sendEventFn func(event interface{})) *HardwareManager {
	mgr := &HardwareManager{
		drivers:          make(map[string]protocol.TrafficDriver),
		heartbeats:       make(map[string]*heartbeat.Manager),
		ipToIntersection: make(map[string]string),
		sendEventFn:      sendEventFn,
	}

	// Trap listener on configured port (default 162)
	mgr.trapListener = traplistener.NewListener(
		trapPort,
		func(event traplistener.TrapEvent) {
			if mgr.sendEventFn != nil {
				mgr.sendEventFn(event)
			}
		},
		func(ip string) string {
			mgr.mu.RLock()
			defer mgr.mu.RUnlock()
			return mgr.ipToIntersection[ip]
		},
	)

	return mgr
}

// Start launches background services such as the UDP SNMP TrapListener.
func (m *HardwareManager) Start() error {
	if err := m.trapListener.Start(); err != nil {
		log.Printf("[HardwareManager] Warning: Failed to start UDP 162 TrapListener (may require root/sudo): %v", err)
	}
	return nil
}

// ApplyAction dispatches a direct command action to the corresponding controller driver.
func (m *HardwareManager) ApplyAction(intersectionID string, actionData map[string]interface{}) (bool, error) {
	m.mu.RLock()
	driver, exists := m.drivers[intersectionID]
	m.mu.RUnlock()

	if !exists {
		return false, fmt.Errorf("intersection %s disconnected", intersectionID)
	}

	return driver.ApplyAction(actionData)
}

// ApplyLogicalAction translates high-level AI action (NEXT_STAGE / HOLD).
func (m *HardwareManager) ApplyLogicalAction(
	intersectionID string,
	action int,
	currentStageIdx int,
	greenStages []int,
	stageCodes map[int]string,
) (bool, error) {
	m.mu.RLock()
	driver, exists := m.drivers[intersectionID]
	m.mu.RUnlock()

	if !exists {
		return false, fmt.Errorf("intersection %s disconnected", intersectionID)
	}

	return driver.ApplyLogicalAction(action, currentStageIdx, greenStages, stageCodes)
}

// ApplyDecision applies pure AI traffic decision ("HOLD" or "ADVANCE") to the intersection.
func (m *HardwareManager) ApplyDecision(intersectionID string, action string) (bool, error) {
	m.mu.RLock()
	driver, exists := m.drivers[intersectionID]
	m.mu.RUnlock()

	if !exists {
		return false, fmt.Errorf("intersection %s disconnected", intersectionID)
	}

	return driver.ApplyDecision(action)
}

// GetTelemetry retrieves real-time telemetry from the intersection controller.
func (m *HardwareManager) GetTelemetry(intersectionID string) (map[string]interface{}, error) {
	m.mu.RLock()
	driver, exists := m.drivers[intersectionID]
	m.mu.RUnlock()

	if !exists {
		return map[string]interface{}{
			"intersection_id": intersectionID,
			"status":          "offline",
			"protocol":        "none",
			"brand":           "Desconectado",
			"model":           "Desconectado",
		}, nil
	}

	return driver.GetTelemetry()
}
