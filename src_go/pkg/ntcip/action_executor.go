// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

import (
	"fmt"
	"log"
	"time"

	"carina/src_go/pkg/protocol"
)

// ApplyAction executes direct hardware commands based on the action dictionary.
func (d *Driver) ApplyAction(actionData map[string]interface{}) (bool, error) {
	actionType, _ := actionData["action_type"].(string)
	if actionType == "" {
		return false, fmt.Errorf("action_type missing")
	}

	stage, hasStage := protocol.ExtractInt(actionData, "stage")
	stageIdx, hasStageIdx := protocol.ExtractInt(actionData, "stage_idx")
	if !hasStageIdx && hasStage && stage > 0 {
		stageIdx = stage - 1
		hasStageIdx = true
	}

	phaseBitmask, hasMask := protocol.ExtractInt(actionData, "stage_mask")
	if !hasMask && hasStageIdx {
		stageCodes := protocol.ExtractStageCodes(actionData)
		phaseBitmask = d.ConvertStageToHardwareMask(stageIdx, d.GreenStages, stageCodes)
	}

	if hasStageIdx && (actionType == "hold" || actionType == "veh_call" || actionType == "demand") {
		d.mu.Lock()
		d.CurrentStage = stageIdx + 1
		d.mu.Unlock()
	}

	switch actionType {
	case "flash":
		d.cancelFailsafeTimer()
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.System.Flash, 1)
		return err == nil, err
	case "release_flash":
		err := d.Client.Set(d.Config.System.Flash, 0)
		return err == nil, err
	case "dark":
		d.cancelFailsafeTimer()
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.System.Dark, 1)
		return err == nil, err
	case "release_dark":
		err := d.Client.Set(d.Config.System.Dark, 0)
		return err == nil, err
	case "release_hold":
		err := d.Client.Set(d.Config.PhaseControl.Hold, 0)
		return err == nil, err
	case "hold":
		d.cancelFailsafeTimer()
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.PhaseControl.Hold, phaseBitmask)
		return err == nil, err
	case "force_off":
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.PhaseControl.ForceOff, phaseBitmask)
		return err == nil, err
	case "omit":
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.PhaseControl.Omit, phaseBitmask)
		return err == nil, err
	case "veh_call", "demand":
		d.cancelFailsafeTimer()
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.PhaseControl.VehCall, phaseBitmask)
		return err == nil, err
	case "ped_call":
		d.clearReleasedFlag()
		err := d.Client.Set(d.Config.PhaseControl.PedCall, phaseBitmask)
		return err == nil, err
	case "ACTIVATE_LOCAL_FIXED_TIME":
		d.clearReleasedFlag()
		clearMs, hasClearMs := protocol.ExtractInt(actionData, "all_red_clear_ms")
		if !hasClearMs || clearMs <= 0 {
			clearMs = d.Config.FailsafeOmitMs
		}
		if clearMs <= 0 {
			clearMs = 2000
		}
		log.Printf("[%s] EXECUTING FAILSAFE: Forcing ALL RED for %d ms (non-blocking release), then releasing to local plans.", d.IPAddress, clearMs)
		allRedMask := 0
		for _, mask := range d.Config.StageToPhaseMap {
			allRedMask |= mask
		}
		if allRedMask == 0 {
			allRedMask = protocol.AllRedMask(d.GreenStages)
		}
		_ = d.Client.Set(d.Config.PhaseControl.ForceOff, allRedMask)
		err := d.Client.Set(d.Config.PhaseControl.Omit, allRedMask)
		if cb := d.getStopHeartbeatCallback(); cb != nil {
			cb()
		}
		d.scheduleOmitClear(time.Duration(clearMs) * time.Millisecond)
		return err == nil, err
	default:
		return false, fmt.Errorf("unknown NTCIP command: %s", actionType)
	}
}
