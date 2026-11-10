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

// EmergencyReleaseControlAll executes global failsafe releasing all active intersections to local plans.
func (m *HardwareManager) EmergencyReleaseControlAll() {
	m.mu.Lock()
	defer m.mu.Unlock()

	log.Printf("[HardwareManager] ALERT: Executing EmergencyReleaseControlAll for %d active controllers...", len(m.drivers))

	// Stop all heartbeats
	for _, hb := range m.heartbeats {
		hb.Stop()
	}
	m.heartbeats = make(map[string]*heartbeat.Manager)

	// Release controllers in parallel with safe timeout
	var wg sync.WaitGroup
	for id, drv := range m.drivers {
		wg.Add(1)
		go func(tlID string, d protocol.TrafficDriver) {
			defer wg.Done()
			log.Printf("[HardwareManager] Fail-safe: Releasing control of traffic light %s...", tlID)
			_, _ = d.ReleaseControl()
			d.Shutdown()
		}(id, drv)
	}

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Println("[HardwareManager] All traffic lights safely released to their local plans.")
	case <-time.After(2 * time.Second):
		log.Println("[HardwareManager] Timeout during emergency release_control.")
	}

	m.drivers = make(map[string]protocol.TrafficDriver)
	m.ipToIntersection = make(map[string]string)
	if m.trapListener != nil {
		m.trapListener.Stop()
	}
}
