// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
