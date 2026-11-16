// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package protocol

import (
	"regexp"
	"strconv"
	"strings"
)

var (
	modelRegex  = regexp.MustCompile(`(?i)\b(ST\d{3,4}|M\d{2,3}|ATC[-_ ]?\d{4}|ASC[/-]?\d+|[A-Z]{1,4}[-_]?\d{3,4})\b`)
	knownBrands = []string{
		"SIEMENS", "PEEK", "SWARCO", "ECONOLITE", "DATAPROM", "TRAFFICWARE",
		"MCCAIN", "YUNEX", "COMPASS", "TELVENT", "KAPSCH",
	}
)

// ExtractBrandAndModel parses manufacturer brand and model from an SNMP sysDescr string.
func ExtractBrandAndModel(sysDescr string) (string, string) {
	if sysDescr == "" {
		return "Não informado", "Não informado"
	}

	descrUpper := strings.ToUpper(sysDescr)
	brand := "Não informado"
	for _, b := range knownBrands {
		if strings.Contains(descrUpper, b) {
			brand = strings.ToUpper(b[:1]) + strings.ToLower(b[1:])
			break
		}
	}

	match := modelRegex.FindString(sysDescr)
	var model string
	if match != "" {
		model = strings.ToUpper(match)
	} else if len(sysDescr) <= 30 {
		model = sysDescr
	} else {
		model = sysDescr[:30] + "..."
	}

	return brand, model
}

// ExtractInt safely reads an integer value decoded from JSON (float64 or int) inside action maps.
func ExtractInt(actionData map[string]interface{}, key string) (int, bool) {
	if actionData == nil {
		return 0, false
	}
	raw, exists := actionData[key]
	if !exists || raw == nil {
		return 0, false
	}
	switch v := raw.(type) {
	case float64:
		return int(v), true
	case int:
		return v, true
	case int64:
		return int(v), true
	default:
		return 0, false
	}
}

// IndexOfStage returns the ordinal position of stageIdx inside greenStages, or -1 if absent.
func IndexOfStage(stageIdx int, greenStages []int) int {
	for i, s := range greenStages {
		if s == stageIdx {
			return i
		}
	}
	return -1
}

// AllRedMask computes the bitmask covering all configured stages or a default 8-phase mask.
func AllRedMask(greenStages []int) int {
	numStages := len(greenStages)
	if numStages <= 0 {
		numStages = 8
	}
	return (1 << numStages) - 1
}

// ExtractStageCodes parses optional stage_codes maps passed via JSON/IPC action dictionaries.
func ExtractStageCodes(actionData map[string]interface{}) map[int]string {
	if actionData == nil {
		return nil
	}
	raw, ok := actionData["stage_codes"]
	if !ok || raw == nil {
		return nil
	}
	if m, ok := raw.(map[int]string); ok {
		return m
	}
	if m, ok := raw.(map[string]interface{}); ok {
		out := make(map[int]string, len(m))
		for k, v := range m {
			if idx, err := strconv.Atoi(k); err == nil {
				if s, isStr := v.(string); isStr {
					out[idx] = s
				}
			}
		}
		return out
	}
	return nil
}
