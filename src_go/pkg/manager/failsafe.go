// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package manager

import (
	"log"
	"sync"
	"time"

	"carina/src_go/pkg/heartbeat"
	"carina/src_go/pkg/protocol"
)

func releaseDriversParallel(drivers map[string]protocol.TrafficDriver, shutdown bool, label string) {
	if len(drivers) == 0 {
		return
	}
	var wg sync.WaitGroup
	for id, drv := range drivers {
		wg.Add(1)
		go func(tlID string, d protocol.TrafficDriver) {
			defer wg.Done()
			log.Printf("[HardwareManager] Fail-safe: %s for traffic light %s...", label, tlID)
			if shutdown {
				d.Shutdown()
			} else {
				_, _ = d.ReleaseControl()
			}
		}(id, drv)
	}

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Printf("[HardwareManager] %s completed for all controllers.", label)
	case <-time.After(2 * time.Second):
		log.Printf("[HardwareManager] Timeout during %s.", label)
	}
}

// EmergencyReleaseControlAll pauses heartbeats and releases control on all active intersections
// while retaining drivers and the SNMP trap listener so ResumeControlAll can recover cleanly.
func (m *HardwareManager) EmergencyReleaseControlAll() {
	m.mu.Lock()
	log.Printf("[HardwareManager] ALERT: Executing EmergencyReleaseControlAll for %d active controllers...", len(m.drivers))
	for _, hb := range m.heartbeats {
		hb.Stop()
	}
	driversCopy := make(map[string]protocol.TrafficDriver, len(m.drivers))
	for id, drv := range m.drivers {
		driversCopy[id] = drv
	}
	m.mu.Unlock()

	releaseDriversParallel(driversCopy, false, "Releasing control")
}

// ResumeControlAll restarts paused controller heartbeats after a Watchdog failsafe recovery.
func (m *HardwareManager) ResumeControlAll() int {
	m.mu.Lock()
	defer m.mu.Unlock()

	resumed := 0
	for _, hb := range m.heartbeats {
		hb.Start()
		resumed++
	}
	if resumed > 0 {
		log.Printf("[HardwareManager] Resumed heartbeats for %d active controller(s).", resumed)
	}
	return resumed
}

// ShutdownAll permanently releases control, closes SNMP sockets, clears maps, and stops traps.
func (m *HardwareManager) ShutdownAll() {
	m.mu.Lock()
	log.Printf("[HardwareManager] Shutting down %d active controllers...", len(m.drivers))

	for _, hb := range m.heartbeats {
		hb.Stop()
	}
	m.heartbeats = make(map[string]*heartbeat.Manager)

	driversCopy := m.drivers
	m.drivers = make(map[string]protocol.TrafficDriver)
	m.ipToIntersection = make(map[string]string)
	trap := m.trapListener
	m.trapListener = nil
	m.mu.Unlock()

	releaseDriversParallel(driversCopy, true, "Shutting down")
	if trap != nil {
		trap.Stop()
	}
}
