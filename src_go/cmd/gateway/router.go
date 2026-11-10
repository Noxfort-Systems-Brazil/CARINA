// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"fmt"

	"carina/src_go/pkg/manager"
	"carina/src_go/web_gateway"
)

// handleCommand routes parsed stdin request envelopes to the corresponding modular command handler (SOLID: SRP, OCP).
func handleCommand(req RequestEnvelope, mgr *manager.HardwareManager, webSrv *web_gateway.WebGatewayServer, out ResponseSender) {
	switch req.Cmd {
	case "ping":
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data:    "pong",
		})

	case "connect", "disconnect", "apply_action", "apply_logical_action", "decision", "get_telemetry", "emergency_release":
		handleHardwareCommand(req, mgr, out)

	case "evp_preempt":
		handleEVPCommand(req, mgr, out)

	case "tailscale_status", "tailscale_enable", "tailscale_disable":
		handleTailscaleCommand(req, webSrv, out)

	case "cco_broadcast", "gateway_set_enabled", "gateway_get_status":
		handleGatewayControlCommand(req, webSrv, out)

	default:
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: false,
			Error:   fmt.Sprintf("unknown command: %s", req.Cmd),
		})
	}
}
