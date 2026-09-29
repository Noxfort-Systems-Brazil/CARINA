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

// File: src_go/pkg/heartbeat/heartbeat.go
// Author: Gabriel Moraes
// Date: September 2026

package heartbeat

import (
	"log"
	"sync"
	"time"
)

// Manager manages the heartbeat pulse cycle for a traffic light controller.
type Manager struct {
	IntersectionID          string
	IPAddress               string
	Interval                time.Duration
	MaxConsecutiveFailures int
	SendPulseFn             func() (bool, error)
	OnLossFn                func(intersectionID string)
	OnRestoreFn             func(intersectionID string)

	mu            sync.Mutex
	stopChan      chan struct{}
	running       bool
	failuresCount int
	isLost        bool
}

// NewManager creates a new instance of the heartbeat manager.
func NewManager(
	intersectionID string,
	ipAddress string,
	interval time.Duration,
	sendPulseFn func() (bool, error),
	onLossFn func(intersectionID string),
	onRestoreFn func(intersectionID string),
) *Manager {
	if interval <= 0 {
		interval = 2 * time.Second
	}

	return &Manager{
		IntersectionID:          intersectionID,
		IPAddress:               ipAddress,
		Interval:                interval,
		MaxConsecutiveFailures: 3,
		SendPulseFn:             sendPulseFn,
		OnLossFn:                onLossFn,
		OnRestoreFn:             onRestoreFn,
		stopChan:                make(chan struct{}),
	}
}

// Start begins the pulse loop in a background goroutine.
func (m *Manager) Start() {
	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return
	}
	m.running = true
	m.stopChan = make(chan struct{})
	m.mu.Unlock()

	go m.loop()
}

// Stop terminates the pulse loop.
func (m *Manager) Stop() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if !m.running {
		return
	}
	m.running = false
	close(m.stopChan)
}

func (m *Manager) loop() {
	ticker := time.NewTicker(m.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopChan:
			return
		case <-ticker.C:
			success := false
			if m.SendPulseFn != nil {
				s, err := m.SendPulseFn()
				success = s && err == nil
			}

			m.mu.Lock()
			if success {
				if m.isLost {
					m.isLost = false
					log.Printf("[%s] Heartbeat RESTABELECIDO para cruzamento %s.", m.IPAddress, m.IntersectionID)
					if m.OnRestoreFn != nil {
						go m.OnRestoreFn(m.IntersectionID)
					}
				}
				m.failuresCount = 0
			} else {
				m.failuresCount++
				if m.failuresCount >= m.MaxConsecutiveFailures && !m.isLost {
					m.isLost = true
					log.Printf("[%s] Heartbeat PERDIDO para cruzamento %s após %d falhas consecutivas!", m.IPAddress, m.IntersectionID, m.failuresCount)
					if m.OnLossFn != nil {
						go m.OnLossFn(m.IntersectionID)
					}
				}
			}
			m.mu.Unlock()
		}
	}
}
