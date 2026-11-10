// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"carina/src_go/pkg/manager"
)

// handleHardwareCommand handles traffic light hardware communication commands (SOLID: SRP).
func handleHardwareCommand(req RequestEnvelope, mgr *manager.HardwareManager, out ResponseSender) {
	switch req.Cmd {
	case "connect":
		info, err := mgr.Connect(req.IntersectionID, req.IP, req.Port, req.Community, req.Protocol, req.GreenStages, req.ConfigPath)
		if err != nil {
			out.Send(ResponseEnvelope{
				ID:      req.ID,
				Type:    "response",
				Success: false,
				Error:   err.Error(),
			})
			return
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data:    info,
		})

	case "disconnect":
		err := mgr.Disconnect(req.IntersectionID)
		if err != nil {
			out.Send(ResponseEnvelope{
				ID:      req.ID,
				Type:    "response",
				Success: false,
				Error:   err.Error(),
			})
			return
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
		})

	case "apply_action":
		success, err := mgr.ApplyAction(req.IntersectionID, req.ActionData)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: success,
			Error:   errMsg,
		})

	case "apply_logical_action":
		success, err := mgr.ApplyLogicalAction(
			req.IntersectionID,
			req.Action,
			req.CurrentStageIdx,
			req.GreenStages,
			req.StageCodes,
		)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: success,
			Error:   errMsg,
		})

	case "decision":
		success, err := mgr.ApplyDecision(req.IntersectionID, req.Decision)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: success,
			Error:   errMsg,
		})

	case "get_telemetry":
		telemetry, err := mgr.GetTelemetry(req.IntersectionID)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}
		out.Send(ResponseEnvelope{
			ID:        req.ID,
			Type:      "response",
			Success:   err == nil,
			Error:     errMsg,
			Telemetry: telemetry,
		})

	case "emergency_release":
		mgr.EmergencyReleaseControlAll()
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
		})
	}
}
