// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"sync"
)

// SSEHub coordinates active Server-Sent Event browser connections for CCO.
// Implements Broadcaster interface.
type SSEHub struct {
	mu      sync.RWMutex
	clients map[chan []byte]bool
}

// NewSSEHub creates a thread-safe SSE broadcast hub.
func NewSSEHub() *SSEHub {
	return &SSEHub{
		clients: make(map[chan []byte]bool),
	}
}

// AddClient registers a new listener channel for push events.
func (h *SSEHub) AddClient(ch chan []byte) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.clients[ch] = true
}

// RemoveClient unregisters and closes a listener channel safely.
func (h *SSEHub) RemoveClient(ch chan []byte) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if _, ok := h.clients[ch]; ok {
		delete(h.clients, ch)
		close(ch)
	}
}

// Broadcast distributes payload bytes non-blockingly to all active connected clients.
func (h *SSEHub) Broadcast(data []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for ch := range h.clients {
		select {
		case ch <- data:
		default:
			// Non-blocking drop if client buffer is saturated to preserve gateway determinism
		}
	}
}

// ClientCount returns the number of currently active streaming clients.
func (h *SSEHub) ClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}
