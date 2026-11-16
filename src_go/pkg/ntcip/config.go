// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
	StatusVehCalls string `json:"status_veh_calls"`
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
	FailsafeOmitMs  int                `json:"failsafe_omit_ms,omitempty"`
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

	if len(cfg.StageToPhaseMap) == 0 {
		cfg.StageToPhaseMap = map[int]int{
			1: 34,
			2: 136,
			3: 17,
			4: 68,
		}
	}

	if cfg.FailsafeOmitMs <= 0 {
		cfg.FailsafeOmitMs = 2000
	}

	return &cfg, nil
}
