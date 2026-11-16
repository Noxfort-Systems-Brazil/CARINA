// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
	"carina/src_go/pkg/snmp"
	"carina/src_go/pkg/utmc"
)

// Connect connects a physical intersection using SNMPv2c credentials or auto-discovery.
func (m *HardwareManager) Connect(
	intersectionID string,
	ip string,
	port int,
	community string,
	protocolName string,
	greenStages []int,
	configPaths ...string,
) (map[string]interface{}, error) {
	var customConfigPath string
	if len(configPaths) > 0 {
		customConfigPath = configPaths[0]
	}
	return m.ConnectWithSNMPConfig(
		intersectionID,
		ip,
		port,
		snmp.SNMPConfig{Version: "2c", Community: community},
		protocolName,
		greenStages,
		customConfigPath,
	)
}

// ConnectWithSNMPConfig connects a physical intersection supporting SNMPv2c and SNMPv3.
func (m *HardwareManager) ConnectWithSNMPConfig(
	intersectionID string,
	ip string,
	port int,
	snmpCfg snmp.SNMPConfig,
	protocolName string,
	greenStages []int,
	customConfigPath string,
) (map[string]interface{}, error) {
	if port <= 0 {
		port = 161
	}
	normCfg := snmpCfg.Normalized()

	// 1. Detach old connection under lock, then close outside mutex
	var prevDriver protocol.TrafficDriver
	var prevHB *heartbeat.Manager
	m.mu.Lock()
	if oldDriver, exists := m.drivers[intersectionID]; exists {
		prevDriver = oldDriver
		if hb, ok := m.heartbeats[intersectionID]; ok {
			prevHB = hb
			delete(m.heartbeats, intersectionID)
		}
		delete(m.drivers, intersectionID)
	}
	m.mu.Unlock()
	if prevHB != nil {
		prevHB.Stop()
	}
	if prevDriver != nil {
		prevDriver.Shutdown()
	}

	// 2. Discover or instantiate driver without holding the manager mutex
	var driver protocol.TrafficDriver
	var err error

	protoUpper := strings.ToUpper(strings.TrimSpace(protocolName))
	switch {
	case strings.Contains(protoUpper, "NTCIP"):
		driver = ntcip.NewDriverWithConfig(ip, port, intersectionID, normCfg, greenStages, customConfigPath)
	case strings.Contains(protoUpper, "UTMC"):
		driver = utmc.NewDriverWithConfig(ip, port, intersectionID, normCfg, greenStages, customConfigPath)
	default:
		driver, err = discovery.DiscoverAndCreateWithConfig(ip, port, normCfg, intersectionID, greenStages, customConfigPath)
		if err != nil {
			return nil, fmt.Errorf("connection and discovery failed for %s (%s:%d): %w", intersectionID, ip, port, err)
		}
	}

	if protoUpper != "" && !strings.EqualFold(protoUpper, "AUTO") {
		if prober, ok := driver.(interface{ Probe() error }); ok {
			if err := prober.Probe(); err != nil {
				if closer, hasClose := driver.(interface{ CloseTransport() }); hasClose {
					closer.CloseTransport()
				} else {
					driver.Shutdown()
				}
				return nil, fmt.Errorf("connection probe failed for %s (%s:%d): %w", intersectionID, ip, port, err)
			}
		}
	}

	// 3. Register driver and start heartbeat under lock (shut down any displaced driver outside mutex)
	var replacedDriver protocol.TrafficDriver
	var replacedHB *heartbeat.Manager
	m.mu.Lock()
	if oldDriver, exists := m.drivers[intersectionID]; exists {
		replacedDriver = oldDriver
		if oldHB, ok := m.heartbeats[intersectionID]; ok {
			replacedHB = oldHB
			delete(m.heartbeats, intersectionID)
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
	if hbCtrl, ok := driver.(interface{ SetStopHeartbeatCallback(func()) }); ok {
		hbCtrl.SetStopHeartbeatCallback(hb.Stop)
	}
	m.heartbeats[intersectionID] = hb
	hb.Start()
	m.mu.Unlock()

	if replacedHB != nil {
		replacedHB.Stop()
	}
	if replacedDriver != nil {
		replacedDriver.Shutdown()
	}

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
	resolvedID, driver, exists := m.resolveDriverLocked(intersectionID)
	if !exists {
		m.mu.Unlock()
		return fmt.Errorf("intersection %s is not connected", intersectionID)
	}
	intersectionID = resolvedID

	hb := m.heartbeats[intersectionID]
	delete(m.heartbeats, intersectionID)
	delete(m.drivers, intersectionID)

	for ip, id := range m.ipToIntersection {
		if id == intersectionID {
			delete(m.ipToIntersection, ip)
			break
		}
	}
	m.mu.Unlock()

	if hb != nil {
		hb.Stop()
	}
	_, _ = driver.ReleaseControl()
	driver.Shutdown()

	log.Printf("[HardwareManager] Intersection %s disconnected successfully.", intersectionID)
	return nil
}
