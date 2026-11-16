// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

import (
	"fmt"
	"strings"

	"carina/src_go/pkg/protocol"
)

// ConvertStageToHardwareMask converts the 0-based stage index to an NTCIP phase bitmask.
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

	if pos := protocol.IndexOfStage(stageIdx, greenStages); pos >= 0 {
		if mask, ok := d.Config.StageToPhaseMap[pos+1]; ok {
			return mask
		}
		return 1 << pos
	}

	if mask, ok := d.Config.StageToPhaseMap[stageNum]; ok {
		return mask
	}

	return 1 << stageIdx
}

// ApplyDecision receives pure AI decision ("HOLD" or "ADVANCE") and physically coordinates signal phases.
func (d *Driver) ApplyDecision(action string) (bool, error) {
	actionUpper := strings.ToUpper(strings.TrimSpace(action))

	d.mu.Lock()
	if actionUpper == "ADVANCE" || actionUpper == "0" {
		maxStages := len(d.Config.StageToPhaseMap)
		if maxStages == 0 {
			maxStages = len(d.GreenStages)
		}
		if maxStages == 0 {
			maxStages = 4
		}
		d.CurrentStage = (d.CurrentStage % maxStages) + 1
	} else if d.CurrentStage <= 0 {
		d.CurrentStage = 1
	}
	stageNum := d.CurrentStage
	d.mu.Unlock()

	mask, ok := d.Config.StageToPhaseMap[stageNum]
	if !ok || mask == 0 {
		mask = 1 << (stageNum - 1)
	}

	d.cancelFailsafeTimer()
	err := d.Client.Set(d.Config.PhaseControl.Hold, mask)
	return err == nil, err
}

// ApplyLogicalAction translates high-level AI actions (0 = NEXT_STAGE, 1 = HOLD) into NTCIP phase sequences.
func (d *Driver) ApplyLogicalAction(action int, currentStageIdx int, greenStages []int, stageCodes map[int]string) (bool, error) {
	if len(greenStages) == 0 {
		return false, fmt.Errorf("greenStages is empty")
	}

	currentListIdx := protocol.IndexOfStage(currentStageIdx, greenStages)
	if currentListIdx == -1 {
		// During yellow/all-red intergreen phases, avoid aborting with error:
		// release active hold on NEXT_STAGE or keep hardware timing its clearance safely.
		if action == 0 {
			return d.ApplyAction(map[string]interface{}{"action_type": "release_hold"})
		}
		return true, nil
	}

	if action == 0 { // NEXT_STAGE
		nextListIdx := (currentListIdx + 1) % len(greenStages)
		targetStageIdx := greenStages[nextListIdx]
		nextStageMask := d.ConvertStageToHardwareMask(targetStageIdx, greenStages, stageCodes)
		currentStageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)

		d.mu.Lock()
		d.CurrentStage = targetStageIdx + 1
		d.mu.Unlock()

		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "release_hold"})
		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "force_off", "stage_mask": currentStageMask})
		return d.ApplyAction(map[string]interface{}{"action_type": "veh_call", "stage_mask": nextStageMask, "stage_idx": targetStageIdx})
	}

	stageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)
	return d.ApplyAction(map[string]interface{}{"action_type": "hold", "stage_mask": stageMask, "stage_idx": currentStageIdx})
}
