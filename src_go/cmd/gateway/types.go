// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"bufio"
	"encoding/json"
	"log"
	"sync"

	"carina/src_go/pkg/snmp"
)

// RequestEnvelope represents an incoming NDJSON command payload from stdin.
type RequestEnvelope struct {
	ID              int64                  `json:"id"`
	Cmd             string                 `json:"cmd"`
	IntersectionID  string                 `json:"intersection_id"`
	IP              string                 `json:"ip"`
	Port            int                    `json:"port"`
	Community       string                 `json:"community"`
	SNMPConfig      *snmp.SNMPConfig       `json:"snmp_config,omitempty"`
	Protocol        string                 `json:"protocol"`
	GreenStages     []int                  `json:"green_stages"`
	ActionData      map[string]interface{} `json:"action_data"`
	Action          int                    `json:"action"`
	Decision        string                 `json:"decision,omitempty"`
	ConfigPath      string                 `json:"config_path,omitempty"`
	CurrentStageIdx int                    `json:"current_stage_idx"`
	StageCodes      map[int]string         `json:"stage_codes"`
	Domain          string                 `json:"domain,omitempty"`
	Token           string                 `json:"token,omitempty"`
	EVPAuthToken    string                 `json:"evp_auth_token,omitempty"`
	CCOAuthToken    string                 `json:"cco_auth_token,omitempty"`
	AllowedOrigin   string                 `json:"allowed_origin,omitempty"`
	Enabled         *bool                  `json:"enabled,omitempty"`
	Data            interface{}            `json:"data,omitempty"`
}

// ResponseEnvelope represents a synchronous command response sent over stdout.
type ResponseEnvelope struct {
	ID        int64       `json:"id"`
	Type      string      `json:"type"` // "response"
	Success   bool        `json:"success"`
	Error     string      `json:"error,omitempty"`
	Data      interface{} `json:"data,omitempty"`
	Telemetry interface{} `json:"telemetry,omitempty"`
}

// ResponseSender defines an abstract sender for command responses and push events.
type ResponseSender interface {
	Send(payload interface{})
}

type stdoutWriter struct {
	mu     sync.Mutex
	writer *bufio.Writer
}

func (w *stdoutWriter) Send(payload interface{}) {
	w.mu.Lock()
	defer w.mu.Unlock()

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("[Gateway Output Error] Failed to serialize JSON: %v", err)
		return
	}

	_, _ = w.writer.Write(data)
	_ = w.writer.WriteByte('\n')
	_ = w.writer.Flush()
}


// IPCHub broadcasts unsolicited push events to all connected clients (stdout and Unix sockets).
type IPCHub struct {
	mu      sync.RWMutex
	senders map[ResponseSender]struct{}
}

func NewIPCHub(initial ...ResponseSender) *IPCHub {
	hub := &IPCHub{
		senders: make(map[ResponseSender]struct{}),
	}
	for _, s := range initial {
		if s != nil {
			hub.senders[s] = struct{}{}
		}
	}
	return hub
}

func (h *IPCHub) Register(s ResponseSender) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.senders[s] = struct{}{}
}

func (h *IPCHub) Unregister(s ResponseSender) {
	h.mu.Lock()
	defer h.mu.Unlock()
	delete(h.senders, s)
}

func (h *IPCHub) Broadcast(payload interface{}) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for s := range h.senders {
		s.Send(payload)
	}
}
