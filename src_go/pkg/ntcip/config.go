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

// File: src_go/pkg/ntcip/config.go
// Author: Gabriel Moraes
// Date: September 2026

package ntcip

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"

	"carina/src_go/configs"
)

// PhaseControlConfig stores NTCIP phase control OIDs.
type PhaseControlConfig struct {
	Hold     string `json:"hold"`
	ForceOff string `json:"force_off"`
	Omit     string `json:"omit"`
	VehCall  string `json:"veh_call"`
	PedCall  string `json:"ped_call"`
}

// TelemetryConfig stores NTCIP telemetry retrieval OIDs.
type TelemetryConfig struct {
	StatusGreens   string `json:"status_greens"`
	StatusYellows  string `json:"status_yellows"`
	StatusReds     string `json:"status_reds"`
	StatusPedCalls string `json:"status_ped_calls"`
}

// SystemConfig stores NTCIP system command OIDs.
type SystemConfig struct {
	Flash     string `json:"flash"`
	Dark      string `json:"dark"`
	Heartbeat string `json:"heartbeat"`
}

// Config encapsulates the complete NTCIP 1202 schema loaded from JSON.
type Config struct {
	PhaseControl    PhaseControlConfig `json:"phase_control"`
	Telemetry       TelemetryConfig    `json:"telemetry"`
	System          SystemConfig       `json:"system"`
	RawStageMap     map[string]int     `json:"stage_to_phase_map"`
	StageToPhaseMap map[int]int        `json:"-"`
}

// LoadConfig loads NTCIP configuration from custom disk path or embedded defaults.
func LoadConfig(customPath string) (*Config, error) {
	var rawData []byte
	var err error

	if customPath != "" {
		if data, readErr := os.ReadFile(customPath); readErr == nil {
			rawData = data
			log.Printf("[NTCIP Config] Loaded custom configuration file: %s", customPath)
		} else {
			log.Printf("[NTCIP Config] Custom file %s not found (%v). Using defaults.", customPath, readErr)
		}
	}

	if len(rawData) == 0 {
		// Attempt standard local project path before falling back to embedded binary
		standardPaths := []string{
			"src_go/configs/ntcip_oids.json",
			"config/ntcip_oids.json",
		}
		for _, p := range standardPaths {
			if data, readErr := os.ReadFile(p); readErr == nil {
				rawData = data
				log.Printf("[NTCIP Config] Loaded from local file path: %s", p)
				break
			}
		}
	}

	if len(rawData) == 0 {
		rawData = configs.DefaultNTCIPJSON
		log.Printf("[NTCIP Config] Loaded from embedded binary (//go:embed).")
	}

	var cfg Config
	if err = json.Unmarshal(rawData, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse NTCIP JSON: %w", err)
	}

	cfg.StageToPhaseMap = make(map[int]int)
	for k, v := range cfg.RawStageMap {
		if stageNum, parseErr := strconv.Atoi(k); parseErr == nil {
			cfg.StageToPhaseMap[stageNum] = v
		}
	}

	// Guarantee default 4-stage map if none provided
	if len(cfg.StageToPhaseMap) == 0 {
		cfg.StageToPhaseMap = map[int]int{
			1: 34,
			2: 136,
			3: 17,
			4: 68,
		}
	}

	return &cfg, nil
}
