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

// File: src_go/pkg/ntcip/action_executor.go
// Author: Gabriel Moraes
// Date: September 2026

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
