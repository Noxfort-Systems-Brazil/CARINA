// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"encoding/json"
	"fmt"
)

// CCOBroadcastUseCase encapsulates the application logic for streaming updates to CCO clients.
// Implements CCOStreamingService.
type CCOBroadcastUseCase struct {
	hub *SSEHub
}

// NewCCOBroadcastUseCase creates a new CCO application service with the specified SSE hub.
func NewCCOBroadcastUseCase(hub *SSEHub) *CCOBroadcastUseCase {
	return &CCOBroadcastUseCase{
		hub: hub,
	}
}

// Broadcast formats and sends payloads to all active CCO clients.
func (s *CCOBroadcastUseCase) Broadcast(payload interface{}) error {
	if s.hub.ClientCount() == 0 {
		return nil
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to serialize CCO broadcast: %w", err)
	}

	sseFormatted := []byte(fmt.Sprintf("data: %s\n\n", data))
	s.hub.Broadcast(sseFormatted)
	return nil
}

// ClientCount returns the number of active streaming CCO clients.
func (s *CCOBroadcastUseCase) ClientCount() int {
	return s.hub.ClientCount()
}

// RegisterClient adds a client channel to the hub.
func (s *CCOBroadcastUseCase) RegisterClient(ch chan []byte) {
	s.hub.AddClient(ch)
}

// UnregisterClient removes a client channel from the hub.
func (s *CCOBroadcastUseCase) UnregisterClient(ch chan []byte) {
	s.hub.RemoveClient(ch)
}

