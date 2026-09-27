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

// File: src_go/cmd/gateway/types.go
// Author: Gabriel Moraes
// Date: September 2026

package main

import (
	"bufio"
	"encoding/json"
	"log"
	"sync"
)

// RequestEnvelope represents an incoming NDJSON command payload from stdin.
type RequestEnvelope struct {
	ID              int64                  `json:"id"`
	Cmd             string                 `json:"cmd"`
	IntersectionID  string                 `json:"intersection_id"`
	IP              string                 `json:"ip"`
	Port            int                    `json:"port"`
	Community       string                 `json:"community"`
	Protocol        string                 `json:"protocol"`
	GreenStages     []int                  `json:"green_stages"`
	ActionData      map[string]interface{} `json:"action_data"`
	Action          int                    `json:"action"`
	Decision        string                 `json:"decision,omitempty"`
	ConfigPath      string                 `json:"config_path,omitempty"`
	CurrentStageIdx int                    `json:"current_stage_idx"`
	StageCodes      map[int]string         `json:"stage_codes"`
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
