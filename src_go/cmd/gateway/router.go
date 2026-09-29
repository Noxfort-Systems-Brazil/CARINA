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

// File: src_go/cmd/gateway/router.go
// Author: Gabriel Moraes
// Date: September 2026

package main

import (
	"fmt"

	"carina/src_go/pkg/manager"
)

// handleCommand routes parsed stdin request envelopes to the corresponding HardwareManager method.
func handleCommand(req RequestEnvelope, mgr *manager.HardwareManager, out *stdoutWriter) {
	switch req.Cmd {
	case "ping":
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data:    "pong",
		})

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

	default:
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: false,
			Error:   fmt.Sprintf("unknown command: %s", req.Cmd),
		})
	}
}
