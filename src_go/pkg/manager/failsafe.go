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

// File: src_go/pkg/manager/failsafe.go
// Author: Gabriel Moraes
// Date: September 2026

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
