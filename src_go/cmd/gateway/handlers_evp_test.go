// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package main

import (
	"testing"

	"carina/src_go/pkg/manager"
)

type spySender struct {
	sent []ResponseEnvelope
}

func (s *spySender) Send(payload interface{}) {
	if resp, ok := payload.(ResponseEnvelope); ok {
		s.sent = append(s.sent, resp)
	}
}

func TestParseStageCodesAndHandleEVPCommand(t *testing.T) {
	parsed := parseStageCodes(map[string]interface{}{
		"0":   "GGrr",
		"2":   "rrGG",
		"bad": "ignored",
	})
	if len(parsed) != 2 || parsed[0] != "GGrr" || parsed[2] != "rrGG" {
		t.Fatalf("Unexpected parsed stage codes: %v", parsed)
	}

	mgr := manager.NewHardwareManager(0, nil)
	out := &spySender{}
	handleEVPCommand(RequestEnvelope{
		ID:             42,
		Cmd:            "evp_preempt",
		IntersectionID: "J99",
		ActionData: map[string]interface{}{
			"action_type":  "activate_preempt",
			"target_stage": float64(2),
			"stage_idx":    float64(2),
			"stage_codes":  map[string]interface{}{"2": "rrGG"},
			"vehicle_id":   "VTR-01",
		},
	}, mgr, out)

	if len(out.sent) != 1 || out.sent[0].ID != 42 || out.sent[0].Data != "HOLD_STAGE_2" {
		t.Fatalf("Unexpected EVP response envelope: %+v", out.sent)
	}
}
