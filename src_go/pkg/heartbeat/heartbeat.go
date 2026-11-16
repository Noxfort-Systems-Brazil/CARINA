// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
	m.failuresCount = 0
	m.isLost = false
	stopCh := make(chan struct{})
	m.stopChan = stopCh
	m.mu.Unlock()

	go m.loop(stopCh)
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

func (m *Manager) loop(stopCh <-chan struct{}) {
	ticker := time.NewTicker(m.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-stopCh:
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
