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

// File: src_go/pkg/ntcip/stage_mapper.go
// Author: Gabriel Moraes
// Date: September 2026

package ntcip

import (
	"fmt"
	"strings"
)

// ConvertStageToHardwareMask converts the stage index to an NTCIP phase bitmask.
func (d *Driver) ConvertStageToHardwareMask(stageIdx int, greenStages []int, stageCodes map[int]string) int {
	stageNum := stageIdx + 1

	if len(greenStages) == 4 {
		if mask, ok := d.Config.StageToPhaseMap[stageNum]; ok {
			return mask
		}
	}

	if stageCodes != nil {
		if stateStr, ok := stageCodes[stageIdx]; ok {
			var mask int
			hasGreenOrYellow := false
			for i, r := range stateStr {
				c := strings.ToLower(string(r))
				if c == "g" || c == "y" {
					hasGreenOrYellow = true
					mask |= 1 << (i % 8)
				}
			}
			if !hasGreenOrYellow {
				return 0 // All red
			}
			return mask
		}
	}

	if mask, ok := d.Config.StageToPhaseMap[stageNum]; ok {
		return mask
	}

	return 1 << stageIdx
}

// ApplyDecision receives pure AI decision ("HOLD" or "ADVANCE") and physically coordinates signal phases.
func (d *Driver) ApplyDecision(action string) (bool, error) {
	actionUpper := strings.ToUpper(strings.TrimSpace(action))

	if actionUpper == "ADVANCE" || actionUpper == "0" {
		maxStages := len(d.Config.StageToPhaseMap)
		if maxStages == 0 {
			maxStages = 4
		}
		d.CurrentStage = (d.CurrentStage % maxStages) + 1
	} else {
		// HOLD
		if d.CurrentStage <= 0 {
			d.CurrentStage = 1
		}
	}

	mask, ok := d.Config.StageToPhaseMap[d.CurrentStage]
	if !ok || mask == 0 {
		mask = 1 << (d.CurrentStage - 1)
	}

	err := d.Client.Set(d.Config.PhaseControl.Hold, mask)
	return err == nil, err
}

// ApplyLogicalAction translates high-level AI actions (0 = NEXT_STAGE, 1 = HOLD) into NTCIP phase sequences.
func (d *Driver) ApplyLogicalAction(action int, currentStageIdx int, greenStages []int, stageCodes map[int]string) (bool, error) {
	if len(greenStages) == 0 {
		return false, fmt.Errorf("greenStages is empty")
	}

	currentListIdx := -1
	for idx, s := range greenStages {
		if s == currentStageIdx {
			currentListIdx = idx
			break
		}
	}
	if currentListIdx == -1 {
		return false, fmt.Errorf("currentStageIdx %d is not in greenStages", currentStageIdx)
	}

	if action == 0 { // NEXT_STAGE
		nextListIdx := (currentListIdx + 1) % len(greenStages)
		targetStageIdx := greenStages[nextListIdx]
		nextStageMask := d.ConvertStageToHardwareMask(targetStageIdx, greenStages, stageCodes)
		currentStageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)

		// 1. Release active hold
		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "release_hold"})
		// 2. Force off current stage
		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "force_off", "stage_mask": currentStageMask})
		// 3. Veh call next stage
		return d.ApplyAction(map[string]interface{}{"action_type": "veh_call", "stage_mask": nextStageMask})
	}

	// HOLD
	stageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)
	return d.ApplyAction(map[string]interface{}{"action_type": "hold", "stage_mask": stageMask})
}
