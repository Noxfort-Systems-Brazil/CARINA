// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

import (
	"fmt"
	"strings"

	"carina/src_go/pkg/protocol"
)

// ConvertStageToHardwareMask converts a 0-based stage index to a UTMC2 stage bitmask.
// When greenStages is sparse (e.g. [0, 3]), stage 3 maps to hardware stage bit 1 (mask 2).
func (d *Driver) ConvertStageToHardwareMask(stageIdx int, greenStages []int, stageCodes map[int]string) int {
	if pos := protocol.IndexOfStage(stageIdx, greenStages); pos >= 0 {
		return 1 << pos
	}

	if stageCodes != nil {
		if stateStr, ok := stageCodes[stageIdx]; ok {
			hasGreen := false
			for _, r := range stateStr {
				if r == 'g' || r == 'G' {
					hasGreen = true
					break
				}
			}
			if !hasGreen {
				return 0
			}
		}
	}

	if stageIdx < 0 {
		return 0
	}
	return 1 << stageIdx
}

// ApplyDecision receives pure AI decision ("HOLD" or "ADVANCE") and physically coordinates stages in UTMC2.
func (d *Driver) ApplyDecision(action string) (bool, error) {
	actionUpper := strings.ToUpper(strings.TrimSpace(action))

	d.mu.Lock()
	numStages := len(d.GreenStages)
	if numStages == 0 {
		numStages = 4
	}

	if actionUpper == "ADVANCE" || actionUpper == "0" {
		d.CurrentStage = (d.CurrentStage % numStages) + 1
	} else if d.CurrentStage <= 0 {
		d.CurrentStage = 1
	}
	logicalPos := d.CurrentStage - 1
	d.mu.Unlock()

	stageMask := 1 << logicalPos
	d.cancelFailsafeTimer()
	err := d.Client.Set(d.Config.StageControl.Hold, stageMask)
	return err == nil, err
}

// ApplyLogicalAction translates high-level AI actions (0 = NEXT_STAGE, 1 = HOLD) into UTMC2 stage sequences.
func (d *Driver) ApplyLogicalAction(action int, currentStageIdx int, greenStages []int, stageCodes map[int]string) (bool, error) {
	if len(greenStages) == 0 {
		return false, fmt.Errorf("greenStages is empty")
	}

	currentListIdx := protocol.IndexOfStage(currentStageIdx, greenStages)
	if currentListIdx == -1 {
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
		d.CurrentStage = nextListIdx + 1
		d.mu.Unlock()

		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "release_hold"})
		_, _ = d.ApplyAction(map[string]interface{}{"action_type": "force_off", "stage_mask": currentStageMask})
		return d.ApplyAction(map[string]interface{}{"action_type": "demand", "stage_mask": nextStageMask, "stage_idx": targetStageIdx})
	}

	stageMask := d.ConvertStageToHardwareMask(currentStageIdx, greenStages, stageCodes)
	return d.ApplyAction(map[string]interface{}{"action_type": "hold", "stage_mask": stageMask, "stage_idx": currentStageIdx})
}
