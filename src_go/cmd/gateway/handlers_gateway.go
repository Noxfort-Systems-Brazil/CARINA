// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"carina/src_go/evp_go"
	"carina/src_go/web_gateway"
)

// handleGatewayControlCommand routes Web Gateway and EVP security management commands (SOLID: SRP).
func handleGatewayControlCommand(req RequestEnvelope, webSrv *web_gateway.WebGatewayServer, evpSrv *evp_go.EVPServer, out ResponseSender) {
	switch req.Cmd {
	case "cco_broadcast":
		if webSrv != nil && req.Data != nil {
			webSrv.BroadcastCCO(req.Data)
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
		})

	case "gateway_set_enabled":
		if webSrv != nil {
			isEnabled := false
			if req.Enabled != nil {
				isEnabled = *req.Enabled
			}
			webSrv.SetEnabled(isEnabled)
		}
		enabledState := false
		if webSrv != nil {
			enabledState = webSrv.IsEnabled()
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data: map[string]interface{}{
				"enabled": enabledState,
			},
		})

	case "gateway_get_status":
		enabledState := false
		port := 2201
		if webSrv != nil {
			enabledState = webSrv.IsEnabled()
			port = webSrv.Port()
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data: map[string]interface{}{
				"enabled": enabledState,
				"port":    port,
			},
		})

	case "gateway_set_auth_tokens":
		if webSrv != nil {
			webSrv.SetAuthTokens(req.EVPAuthToken, req.CCOAuthToken)
			if req.AllowedOrigin != "" {
				webSrv.SetAllowedOrigin(req.AllowedOrigin)
			}
		}
		if evpSrv != nil {
			evpSrv.SetMasterToken(req.EVPAuthToken)
		}
		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: true,
			Data: map[string]interface{}{
				"evp_auth_configured": req.EVPAuthToken != "",
				"cco_auth_configured": req.CCOAuthToken != "",
			},
		})
	}
}
