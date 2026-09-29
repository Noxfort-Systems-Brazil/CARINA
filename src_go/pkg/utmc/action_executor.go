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

// File: src_go/pkg/utmc/action_executor.go
// Author: Gabriel Moraes
// Date: September 2026

package utmc

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

	var stageBitmask int
	if sm, ok := actionData["stage_mask"].(float64); ok {
		stageBitmask = int(sm)
	} else if sm, ok := actionData["stage_mask"].(int); ok {
		stageBitmask = sm
	} else if stage > 0 {
		stageBitmask = 1 << (stage - 1)
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
		err := d.Client.Set(d.Config.StageControl.Hold, 0)
		return err == nil, err
	case "hold":
		err := d.Client.Set(d.Config.StageControl.Hold, stageBitmask)
		return err == nil, err
	case "force_off":
		err := d.Client.Set(d.Config.StageControl.ForceOff, stageBitmask)
		return err == nil, err
	case "omit":
		err := d.Client.Set(d.Config.StageControl.Omit, stageBitmask)
		return err == nil, err
	case "demand", "veh_call":
		err := d.Client.Set(d.Config.Telemetry.StatusDemand, stageBitmask)
		return err == nil, err
	case "extend":
		err := d.Client.Set(d.Config.StageControl.Extend, stageBitmask)
		return err == nil, err
	case "ACTIVATE_LOCAL_FIXED_TIME":
		log.Printf("[%s] EXECUTING FAILSAFE: Forcing ALL RED for 2 seconds, then releasing to local plans.", d.IPAddress)
		numStages := len(d.GreenStages)
		if numStages == 0 {
			numStages = 8
		}
		allRedMask := (1 << numStages) - 1

		_ = d.Client.Set(d.Config.StageControl.ForceOff, allRedMask)
		_ = d.Client.Set(d.Config.StageControl.Omit, allRedMask)
		time.Sleep(2 * time.Second)
		err := d.Client.Set(d.Config.StageControl.Omit, 0)
		if d.StopHeartbeatCb != nil {
			d.StopHeartbeatCb()
		}
		return err == nil, err
	default:
		return false, fmt.Errorf("unknown UTMC2 command: %s", actionType)
	}
}
