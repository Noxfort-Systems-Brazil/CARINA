// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
