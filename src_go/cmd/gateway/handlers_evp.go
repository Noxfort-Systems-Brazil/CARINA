// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"strconv"

	"carina/src_go/evp_go"
	"carina/src_go/pkg/manager"
)

func parseStageCodes(raw interface{}) map[int]string {
	rawMap, ok := raw.(map[string]interface{})
	if !ok || len(rawMap) == 0 {
		return nil
	}
	parsed := make(map[int]string, len(rawMap))
	for k, v := range rawMap {
		idx, err := strconv.Atoi(k)
		if err != nil {
			continue
		}
		if code, ok := v.(string); ok {
			parsed[idx] = code
		}
	}
	if len(parsed) == 0 {
		return nil
	}
	return parsed
}

// handleEVPCommand routes emergency vehicle preemption commands (SOLID: SRP).
func handleEVPCommand(req RequestEnvelope, mgr *manager.HardwareManager, out ResponseSender) {
	dispatcher := evp_go.NewDispatcher(mgr)
	actionType := "activate_preempt"
	targetStage := 1
	var stageIdx *int
	stageCodes := req.StageCodes
	vehicleID := ""

	if req.ActionData != nil {
		if at, ok := req.ActionData["action_type"].(string); ok && at != "" {
			actionType = at
		}
		if stg, ok := req.ActionData["target_stage"].(float64); ok {
			targetStage = int(stg)
		} else if stg, ok := req.ActionData["target_stage"].(int); ok {
			targetStage = stg
		}
		if idx, ok := req.ActionData["stage_idx"].(float64); ok {
			val := int(idx)
			stageIdx = &val
		} else if idx, ok := req.ActionData["stage_idx"].(int); ok {
			val := idx
			stageIdx = &val
		}
		if len(stageCodes) == 0 {
			stageCodes = parseStageCodes(req.ActionData["stage_codes"])
		}
		if vid, ok := req.ActionData["vehicle_id"].(string); ok {
			vehicleID = vid
		}
	}

	res := dispatcher.ExecutePreemption(evp_go.PreemptionCommand{
		IntersectionID: req.IntersectionID,
		ActionType:     actionType,
		TargetStage:    targetStage,
		StageIdx:       stageIdx,
		StageCodes:     stageCodes,
		VehicleID:      vehicleID,
	})

	out.Send(ResponseEnvelope{
		ID:      req.ID,
		Type:    "response",
		Success: res.Success,
		Error:   res.Error,
		Data:    res.ActionExecuted,
	})
}
