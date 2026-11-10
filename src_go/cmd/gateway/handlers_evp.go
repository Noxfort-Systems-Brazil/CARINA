// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"carina/src_go/evp_go"
	"carina/src_go/pkg/manager"
)

// handleEVPCommand routes emergency vehicle preemption commands (SOLID: SRP).
func handleEVPCommand(req RequestEnvelope, mgr *manager.HardwareManager, out ResponseSender) {
	dispatcher := evp_go.NewDispatcher(mgr)
	actionType := "activate_preempt"
	targetStage := 1
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
		if vid, ok := req.ActionData["vehicle_id"].(string); ok {
			vehicleID = vid
		}
	}

	res := dispatcher.ExecutePreemption(evp_go.PreemptionCommand{
		IntersectionID: req.IntersectionID,
		ActionType:     actionType,
		TargetStage:    targetStage,
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
