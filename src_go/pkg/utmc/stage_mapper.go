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

// File: src_go/pkg/utmc/stage_mapper.go
// Author: Gabriel Moraes
// Date: September 2026

package utmc

import (
	"fmt"
	"strings"
)

// ConvertStageToHardwareMask converts stage index to UTMC2 bitmask (bit stage_idx).
func (d *Driver) ConvertStageToHardwareMask(stageIdx int, greenStages []int, stageCodes map[int]string) int {
	return 1 << stageIdx
}

// ApplyDecision receives pure AI decision ("HOLD" or "ADVANCE") and physically coordinates stages in UTMC2.
func (d *Driver) ApplyDecision(action string) (bool, error) {
	actionUpper := strings.ToUpper(strings.TrimSpace(action))

	numStages := len(d.GreenStages)
	if numStages == 0 {
		numStages = 4
	}

	if actionUpper == "ADVANCE" || actionUpper == "0" {
		d.CurrentStage = (d.CurrentStage % numStages) + 1
	} else {
		// HOLD
		if d.CurrentStage <= 0 {
			d.CurrentStage = 1
		}
	}

	stageMask := 1 << (d.CurrentStage - 1)
	err := d.Client.Set(d.Config.StageControl.Hold, stageMask)
	return err == nil, err
}

// ApplyLogicalAction translates high-level AI actions (0 = NEXT_STAGE, 1 = HOLD) into UTMC2 stage sequences.
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
		// 3. Demand next stage
		return d.ApplyAction(map[string]interface{}{"action_type": "demand", "stage_mask": nextStageMask})
	}

	// HOLD
	stageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)
	return d.ApplyAction(map[string]interface{}{"action_type": "hold", "stage_mask": stageMask})
}
