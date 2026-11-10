// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

import (
	"fmt"
	"log"
	"time"
)

// ApplyAction executes direct hardware commands based on the action dictionary.
func (d *Driver) ApplyAction(actionData map[string]interface{}) (bool, error) {
	actionType, _ := actionData["action_type"].(string)
	if actionType == "" {
		return false, fmt.Errorf("action_type missing")
	}

	var stage int
	if s, ok := actionData["stage"].(float64); ok {
		stage = int(s)
	} else if s, ok := actionData["stage"].(int); ok {
		stage = s
	}

	var phaseBitmask int
	if sm, ok := actionData["stage_mask"].(float64); ok {
		phaseBitmask = int(sm)
	} else if sm, ok := actionData["stage_mask"].(int); ok {
		phaseBitmask = sm
	} else if stage > 0 {
		if m, ok := d.Config.StageToPhaseMap[stage]; ok {
			phaseBitmask = m
		} else {
			phaseBitmask = 1 << (stage - 1)
		}
	}

	switch actionType {
	case "flash":
		err := d.Client.Set(d.Config.System.Flash, 1)
		return err == nil, err
	case "release_flash":
		err := d.Client.Set(d.Config.System.Flash, 0)
		return err == nil, err
	case "dark":
		err := d.Client.Set(d.Config.System.Dark, 1)
		return err == nil, err
	case "release_dark":
		err := d.Client.Set(d.Config.System.Dark, 0)
		return err == nil, err
	case "release_hold":
		err := d.Client.Set(d.Config.PhaseControl.Hold, 0)
		return err == nil, err
	case "hold":
		err := d.Client.Set(d.Config.PhaseControl.Hold, phaseBitmask)
		return err == nil, err
	case "force_off":
		err := d.Client.Set(d.Config.PhaseControl.ForceOff, phaseBitmask)
		return err == nil, err
	case "omit":
		err := d.Client.Set(d.Config.PhaseControl.Omit, phaseBitmask)
		return err == nil, err
	case "veh_call":
		err := d.Client.Set(d.Config.PhaseControl.VehCall, phaseBitmask)
		return err == nil, err
	case "ped_call":
		err := d.Client.Set(d.Config.PhaseControl.PedCall, phaseBitmask)
		return err == nil, err
	case "ACTIVATE_LOCAL_FIXED_TIME":
		log.Printf("[%s] EXECUTING FAILSAFE: Forcing ALL RED for 2 seconds, then releasing to local plans.", d.IPAddress)
		allRedMask := 0
		for _, mask := range d.Config.StageToPhaseMap {
			allRedMask |= mask
		}
		if allRedMask == 0 {
			numStages := len(d.GreenStages)
			if numStages == 0 {
				numStages = 8
			}
			allRedMask = (1 << numStages) - 1
		}
		_ = d.Client.Set(d.Config.PhaseControl.ForceOff, allRedMask)
		_ = d.Client.Set(d.Config.PhaseControl.Omit, allRedMask)
		time.Sleep(2 * time.Second)
		err := d.Client.Set(d.Config.PhaseControl.Omit, 0)
		if d.StopHeartbeatCb != nil {
			d.StopHeartbeatCb()
		}
		return err == nil, err
	default:
		return false, fmt.Errorf("unknown NTCIP command: %s", actionType)
	}
}
