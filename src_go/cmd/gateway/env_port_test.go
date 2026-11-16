// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import "testing"

func TestResolvePortFlagOrEnv(t *testing.T) {
	t.Setenv("CARINA_TRAP_PORT", "16200")
	t.Setenv("CARINA_GATEWAY_PORT", "2299")

	if port := resolvePortFlagOrEnv(map[string]bool{}, "trap-port", 162, "CARINA_TRAP_PORT"); port != 16200 {
		t.Errorf("Expected CARINA_TRAP_PORT=16200 to override default, got %d", port)
	}
	if port := resolvePortFlagOrEnv(map[string]bool{"trap-port": true}, "trap-port", 1162, "CARINA_TRAP_PORT"); port != 1162 {
		t.Errorf("Expected explicit CLI flag to win over env var, got %d", port)
	}
	if port := resolvePortFlagOrEnv(map[string]bool{}, "web-port", 2201, "CARINA_GATEWAY_PORT"); port != 2299 {
		t.Errorf("Expected CARINA_GATEWAY_PORT=2299 to override default, got %d", port)
	}

	t.Setenv("CARINA_TRAP_PORT", "not-a-port")
	if port := resolvePortFlagOrEnv(map[string]bool{}, "trap-port", 162, "CARINA_TRAP_PORT"); port != 162 {
		t.Errorf("Expected invalid env port to fall back to default 162, got %d", port)
	}
}
