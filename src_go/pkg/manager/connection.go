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

// File: src_go/pkg/manager/connection.go
// Author: Gabriel Moraes
// Date: September 2026

package manager

import (
	"fmt"
	"log"
	"strings"
	"time"

	"carina/src_go/pkg/discovery"
	"carina/src_go/pkg/heartbeat"
	"carina/src_go/pkg/ntcip"
	"carina/src_go/pkg/protocol"
	"carina/src_go/pkg/utmc"
)

// Connect connects a physical intersection to a specific driver or initiates auto-discovery.
func (m *HardwareManager) Connect(
	intersectionID string,
	ip string,
	port int,
	community string,
	protocolName string,
	greenStages []int,
	configPaths ...string,
) (map[string]interface{}, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	var customConfigPath string
	if len(configPaths) > 0 {
		customConfigPath = configPaths[0]
	}

	// If already connected, close previous connection cleanly
	if oldDriver, exists := m.drivers[intersectionID]; exists {
		if hb, ok := m.heartbeats[intersectionID]; ok {
			hb.Stop()
			delete(m.heartbeats, intersectionID)
		}
		oldDriver.Shutdown()
		delete(m.drivers, intersectionID)
	}

	if port <= 0 {
		port = 161
	}
	if community == "" {
		community = "public"
	}

	var driver protocol.TrafficDriver
	var err error

	protoUpper := strings.ToUpper(strings.TrimSpace(protocolName))
	switch {
	case strings.Contains(protoUpper, "NTCIP"):
		d := ntcip.NewDriver(ip, port, intersectionID, community, greenStages, customConfigPath)
		driver = d
	case strings.Contains(protoUpper, "UTMC"):
		d := utmc.NewDriver(ip, port, intersectionID, community, greenStages, customConfigPath)
		driver = d
	default:
		// Auto-discovery
		driver, err = discovery.DiscoverAndCreate(ip, port, community, intersectionID, greenStages)
		if err != nil {
			return nil, fmt.Errorf("connection and discovery failed for %s (%s:%d): %w", intersectionID, ip, port, err)
		}
	}

	m.drivers[intersectionID] = driver
	m.ipToIntersection[ip] = intersectionID

	// Start dedicated heartbeat watchdog
	hb := heartbeat.NewManager(
		intersectionID,
		ip,
		2*time.Second,
		func() (bool, error) {
			return driver.SendHeartbeatPulse()
		},
		func(id string) {
			if m.sendEventFn != nil {
				m.sendEventFn(map[string]interface{}{
					"type":            "event",
					"event_type":      "heartbeat_lost",
					"intersection_id": id,
					"ip":              ip,
					"timestamp":       time.Now().UTC().Format(time.RFC3339),
				})
			}
		},
		func(id string) {
			if m.sendEventFn != nil {
				m.sendEventFn(map[string]interface{}{
					"type":            "event",
					"event_type":      "heartbeat_restored",
					"intersection_id": id,
					"ip":              ip,
					"timestamp":       time.Now().UTC().Format(time.RFC3339),
				})
			}
		},
	)
	m.heartbeats[intersectionID] = hb
	hb.Start()

	log.Printf("[HardwareManager] Intersection %s successfully connected at %s:%d via %s.", intersectionID, ip, port, driver.GetProtocolName())

	return map[string]interface{}{
		"intersection_id": intersectionID,
		"protocol":        driver.GetProtocolName(),
		"brand":           driver.GetBrand(),
		"model":           driver.GetModel(),
		"is_connected":    true,
	}, nil
}

// Disconnect terminates the intersection connection and releases remote control.
func (m *HardwareManager) Disconnect(intersectionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	driver, exists := m.drivers[intersectionID]
	if !exists {
		altID := ""
		if strings.HasPrefix(intersectionID, "tl_") {
			altID = strings.TrimPrefix(intersectionID, "tl_")
		} else {
			altID = "tl_" + intersectionID
		}
		if d, ok := m.drivers[altID]; ok {
			driver = d
			exists = true
			intersectionID = altID
		}
	}
	if !exists {
		return fmt.Errorf("intersection %s is not connected", intersectionID)
	}

	if hb, ok := m.heartbeats[intersectionID]; ok {
		hb.Stop()
		delete(m.heartbeats, intersectionID)
	}

	_, _ = driver.ReleaseControl()
	driver.Shutdown()
	delete(m.drivers, intersectionID)

	// Remove from IP mapping
	for ip, id := range m.ipToIntersection {
		if id == intersectionID {
			delete(m.ipToIntersection, ip)
			break
		}
	}

	log.Printf("[HardwareManager] Intersection %s disconnected successfully.", intersectionID)
	return nil
}
