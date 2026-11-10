// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

import (
	"encoding/json"
	"fmt"
	"log"
	"os"

	"carina/src_go/configs"
)

// StageControlConfig stores UTMC2 stage control OIDs.
type StageControlConfig struct {
	Hold     string `json:"hold"`
	ForceOff string `json:"force_off"`
	Omit     string `json:"omit"`
	Extend   string `json:"extend"`
}

// TelemetryConfig stores UTMC2 telemetry query OIDs.
type TelemetryConfig struct {
	StatusActive    string `json:"status_active"`
	StatusDemand    string `json:"status_demand"`
	StatusLeaving   string `json:"status_leaving"`
	StatusPedDemand string `json:"status_ped_demand"`
}

// SystemConfig stores UTMC2 system command OIDs.
type SystemConfig struct {
	Flash    string `json:"flash"`
	Dark     string `json:"dark"`
	Watchdog string `json:"watchdog"`
}

// Config encapsulates the complete UTMC2 schema loaded from JSON.
type Config struct {
	StageControl StageControlConfig `json:"stage_control"`
	Telemetry    TelemetryConfig    `json:"telemetry"`
	System       SystemConfig       `json:"system"`
}

// LoadConfig loads UTMC configuration from custom disk path or embedded defaults.
func LoadConfig(customPath string) (*Config, error) {
	var rawData []byte
	var err error

	if customPath != "" {
		if data, readErr := os.ReadFile(customPath); readErr == nil {
			rawData = data
			log.Printf("[UTMC Config] Loaded custom configuration file: %s", customPath)
		} else {
			log.Printf("[UTMC Config] Custom file %s not found (%v). Using defaults.", customPath, readErr)
		}
	}

	if len(rawData) == 0 {
		standardPaths := []string{
			"src_go/configs/utmc_oids.json",
			"config/utmc_oids.json",
		}
		for _, p := range standardPaths {
			if data, readErr := os.ReadFile(p); readErr == nil {
				rawData = data
				log.Printf("[UTMC Config] Loaded from local file path: %s", p)
				break
			}
		}
	}

	if len(rawData) == 0 {
		rawData = configs.DefaultUTMCJSON
		log.Printf("[UTMC Config] Loaded from embedded binary (//go:embed).")
	}

	var cfg Config
	if err = json.Unmarshal(rawData, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse UTMC JSON: %w", err)
	}

	return &cfg, nil
}
