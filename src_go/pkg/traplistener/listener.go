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

// File: src_go/pkg/traplistener/listener.go
// Author: Gabriel Moraes
// Date: September 2026

package traplistener

import (
	"fmt"
	"log"
	"net"
	"sync"
	"time"
)

// TrapEvent represents a structured hardware alarm/notification event.
type TrapEvent struct {
	Type           string `json:"type"`
	EventType      string `json:"event_type"`
	IntersectionID string `json:"intersection_id"`
	OID            string `json:"oid"`
	Level          string `json:"level"`
	Category       string `json:"category"`
	Details        string `json:"details"`
	SourceIP       string `json:"source_ip"`
	Timestamp      string `json:"timestamp"`
}

// Listener listens for active SNMP Traps on a UDP socket (default port 162).
// Delegates payload decoding to parser.go.
type Listener struct {
	Port                int
	OnTrapReceived      func(event TrapEvent)
	GetIntersectionByIP func(ip string) string

	mu       sync.Mutex
	conn     *net.UDPConn
	running  bool
	stopChan chan struct{}
}

// NewListener creates a new TrapListener instance.
func NewListener(port int, onTrapReceived func(event TrapEvent), getIntersectionByIP func(ip string) string) *Listener {
	if port <= 0 {
		port = 162
	}
	return &Listener{
		Port:                port,
		OnTrapReceived:      onTrapReceived,
		GetIntersectionByIP: getIntersectionByIP,
		stopChan:            make(chan struct{}),
	}
}

// Start opens the UDP socket on the configured port.
func (l *Listener) Start() error {
	l.mu.Lock()
	if l.running {
		l.mu.Unlock()
		return nil
	}

	addr := &net.UDPAddr{
		Port: l.Port,
		IP:   net.ParseIP("0.0.0.0"),
	}

	conn, err := net.ListenUDP("udp", addr)
	if err != nil {
		l.mu.Unlock()
		return fmt.Errorf("failed to open UDP socket on port %d for Traps: %w", l.Port, err)
	}

	l.conn = conn
	l.running = true
	l.stopChan = make(chan struct{})
	l.mu.Unlock()

	log.Printf("[TrapListener] Listening for SNMP Traps on UDP :%d...", l.Port)
	go l.listenLoop()
	return nil
}

// Stop closes the UDP socket.
func (l *Listener) Stop() {
	l.mu.Lock()
	defer l.mu.Unlock()
	if !l.running {
		return
	}
	l.running = false
	close(l.stopChan)
	if l.conn != nil {
		_ = l.conn.Close()
		l.conn = nil
	}
}

func (l *Listener) listenLoop() {
	buf := make([]byte, 8192)

	for {
		select {
		case <-l.stopChan:
			return
		default:
			l.mu.Lock()
			conn := l.conn
			l.mu.Unlock()

			if conn == nil {
				return
			}

			_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
			n, remoteAddr, err := conn.ReadFromUDP(buf)
			if err != nil {
				if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
					continue
				}
				select {
				case <-l.stopChan:
					return
				default:
					continue
				}
			}

			if n > 0 {
				raw := string(buf[:n])
				srcIP := remoteAddr.IP.String()
				event := l.parsePayload(raw, srcIP)

				log.Printf("[TrapListener] Alert received from %s (%s) [%s]: %s",
					srcIP, event.IntersectionID, event.Level, event.Details)

				if l.OnTrapReceived != nil {
					l.OnTrapReceived(event)
				}
			}
		}
	}
}
