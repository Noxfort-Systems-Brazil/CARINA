// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"carina/src_go/pkg/manager"
	"carina/src_go/pkg/snmp"
)

// handleHardwareCommand handles traffic light hardware communication commands (SOLID: SRP).
func handleHardwareCommand(req RequestEnvelope, mgr *manager.HardwareManager, out ResponseSender) {
	switch req.Cmd {
	case "connect":
		snmpCfg := snmp.SNMPConfig{
			Version:   "2c",
			Community: req.Community,
		}
		if req.SNMPConfig != nil {
			snmpCfg = *req.SNMPConfig
			if snmpCfg.Community == "" && req.Community != "" {
				snmpCfg.Community = req.Community
			}
		}
		info, err := mgr.ConnectWithSNMPConfig(
			req.IntersectionID,
			req.IP,
			req.Port,
			snmpCfg,
			req.Protocol,
			req.GreenStages,
			req.ConfigPath,
		)
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

	case "resume_control":
		resumed := mgr.ResumeControlAll()
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data:    map[string]interface{}{"resumed_count": resumed},
		})
	}
}
