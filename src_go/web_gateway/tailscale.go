// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// CommandRunner abstracts local CLI execution for testability.
type CommandRunner func(ctx context.Context, name string, args ...string) ([]byte, error)

func defaultCommandRunner(ctx context.Context, name string, args ...string) ([]byte, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	return cmd.CombinedOutput()
}

// TailscaleStatus represents the current state of the Tailscale Gateway and Funnel.
type TailscaleStatus struct {
	Success      bool   `json:"success"`
	Installed    bool   `json:"installed"`
	Running      bool   `json:"running"`
	FunnelActive bool   `json:"funnel_active"`
	Domain       string `json:"domain"`
	CCOUrl       string `json:"cco_url"`
	EVPUrl       string `json:"evp_url"`
	Message      string `json:"message"`
	Error        string `json:"error,omitempty"`
}

// TailscaleClient manages automatic Tailscale Funnel lifecycle and status queries.
type TailscaleClient struct {
	runner CommandRunner
}

// NewTailscaleClient creates a new TailscaleClient using the standard OS command runner.
func NewTailscaleClient() *TailscaleClient {
	return &TailscaleClient{
		runner: defaultCommandRunner,
	}
}

// NewTailscaleClientWithRunner creates a TailscaleClient with a custom runner for unit tests.
func NewTailscaleClientWithRunner(runner CommandRunner) *TailscaleClient {
	if runner == nil {
		runner = defaultCommandRunner
	}
	return &TailscaleClient{
		runner: runner,
	}
}

// CleanDomain strips protocol prefixes, slashes, and trailing dots from a domain name.
func CleanDomain(raw string) string {
	d := strings.TrimSpace(raw)
	d = strings.TrimPrefix(d, "https://")
	d = strings.TrimPrefix(d, "http://")
	d = strings.TrimSuffix(d, "/")
	d = strings.TrimSuffix(d, ".")
	return d
}

// FormatServiceURLs constructs the standardized CCO and EVP URLs from a Tailscale domain.
func FormatServiceURLs(domain string) (ccoURL, evpURL string) {
	clean := CleanDomain(domain)
	if clean == "" {
		return "", ""
	}
	return fmt.Sprintf("https://%s/cco", clean), fmt.Sprintf("https://%s/amb/v1", clean)
}

type tailscaleStatusJSON struct {
	BackendState string   `json:"BackendState"`
	CertDomains  []string `json:"CertDomains"`
	Self         *struct {
		DNSName string `json:"DNSName"`
		Online  bool   `json:"Online"`
	} `json:"Self"`
}

type tailscaleFunnelJSON struct {
	AllowFunnel map[string]bool        `json:"AllowFunnel"`
	Web         map[string]interface{} `json:"Web"`
}

// GetStatus inspects the local Tailscale daemon and Funnel state.
func (c *TailscaleClient) GetStatus(ctx context.Context) TailscaleStatus {
	out, err := c.runner(ctx, "tailscale", "status", "--json")
	if err != nil && len(out) == 0 {
		return TailscaleStatus{
			Success:   false,
			Installed: false,
			Error:     "Tailscale não encontrado no sistema. Instale o Tailscale para ativar o Gateway Remoto.",
		}
	}

	var tsStatus tailscaleStatusJSON
	if jsonErr := json.Unmarshal(out, &tsStatus); jsonErr != nil {
		msg := strings.TrimSpace(string(out))
		if msg == "" && err != nil {
			msg = err.Error()
		}
		return TailscaleStatus{
			Success:   false,
			Installed: true,
			Running:   false,
			Error:     fmt.Sprintf("Tailscale desconectado ou indisponível: %s", msg),
		}
	}

	running := tsStatus.BackendState == "Running"
	var domain string
	if len(tsStatus.CertDomains) > 0 {
		domain = CleanDomain(tsStatus.CertDomains[0])
	} else if tsStatus.Self != nil && tsStatus.Self.DNSName != "" {
		domain = CleanDomain(tsStatus.Self.DNSName)
	}

	if !running {
		return TailscaleStatus{
			Success:   false,
			Installed: true,
			Running:   false,
			Domain:    domain,
			Error:     fmt.Sprintf("Tailscale não está autenticado (estado: %s). Execute 'sudo tailscale up'.", tsStatus.BackendState),
		}
	}

	funnelActive := false
	fOut, fErr := c.runner(ctx, "tailscale", "funnel", "status", "--json")
	if fErr == nil && len(fOut) > 0 {
		var fStatus tailscaleFunnelJSON
		if json.Unmarshal(fOut, &fStatus) == nil {
			for _, allowed := range fStatus.AllowFunnel {
				if allowed {
					funnelActive = true
					break
				}
			}
		}
	}

	ccoURL, evpURL := FormatServiceURLs(domain)
	msg := "Tailscale conectado"
	if funnelActive {
		msg = "Tailscale Funnel ativo e público"
	}

	return TailscaleStatus{
		Success:      true,
		Installed:    true,
		Running:      true,
		FunnelActive: funnelActive,
		Domain:       domain,
		CCOUrl:       ccoURL,
		EVPUrl:       evpURL,
		Message:      msg,
	}
}

// EnableFunnel activates the Tailscale Funnel in the background for the given local port.
func (c *TailscaleClient) EnableFunnel(ctx context.Context, port int) TailscaleStatus {
	if port <= 0 {
		port = 2201
	}

	status := c.GetStatus(ctx)
	if !status.Installed || !status.Running {
		return status
	}

	out, err := c.runner(ctx, "tailscale", "funnel", "--bg", strconv.Itoa(port))
	outStr := strings.TrimSpace(string(out))
	if err != nil {
		return TailscaleStatus{
			Success:   false,
			Installed: true,
			Running:   true,
			Domain:    status.Domain,
			Error:     fmt.Sprintf("Falha ao ativar Tailscale Funnel: %s (%v)", outStr, err),
		}
	}

	updated := c.GetStatus(ctx)
	updated.FunnelActive = true
	if updated.Domain != "" {
		updated.CCOUrl, updated.EVPUrl = FormatServiceURLs(updated.Domain)
	}
	updated.Success = true
	updated.Message = "Tailscale Funnel ativado com sucesso"
	return updated
}

// DisableFunnel turns off the active Tailscale Funnel.
func (c *TailscaleClient) DisableFunnel(ctx context.Context) TailscaleStatus {
	_, _ = c.runner(ctx, "tailscale", "funnel", "--https=443", "off")
	status := c.GetStatus(ctx)
	status.FunnelActive = false
	status.Success = true
	status.Message = "Tailscale Funnel desativado"
	return status
}
