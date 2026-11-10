// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"context"
	"time"

	"carina/src_go/web_gateway"
)

// handleTailscaleCommand routes Tailscale mesh connectivity commands (SOLID: SRP).
func handleTailscaleCommand(req RequestEnvelope, webSrv *web_gateway.WebGatewayServer, out ResponseSender) {
	switch req.Cmd {
	case "tailscale_status":
		client := web_gateway.NewTailscaleClient()
		if webSrv != nil && webSrv.Tailscale() != nil {
			client = webSrv.Tailscale()
		}
		ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
		res := client.GetStatus(ctx)
		cancel()

		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: res.Success,
			Error:   res.Error,
			Data:    res,
		})

	case "tailscale_enable":
		client := web_gateway.NewTailscaleClient()
		port := 2201
		if webSrv != nil {
			if webSrv.Tailscale() != nil {
				client = webSrv.Tailscale()
			}
			port = webSrv.Port()
		}
		if req.Port > 0 {
			port = req.Port
		}
		ctx, cancel := context.WithTimeout(context.Background(), 12*time.Second)
		res := client.EnableFunnel(ctx, port)
		cancel()

		if res.Success && webSrv != nil {
			webSrv.SetEnabled(true)
		}

		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: res.Success,
			Error:   res.Error,
			Data:    res,
		})

	case "tailscale_disable":
		client := web_gateway.NewTailscaleClient()
		if webSrv != nil && webSrv.Tailscale() != nil {
			client = webSrv.Tailscale()
		}
		ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
		res := client.DisableFunnel(ctx)
		cancel()

		if webSrv != nil {
			webSrv.SetEnabled(false)
		}

		out.Send(ResponseEnvelope{
			ID:      req.ID,
			Type:    "response",
			Success: res.Success,
			Error:   res.Error,
			Data:    res,
		})
	}
}
