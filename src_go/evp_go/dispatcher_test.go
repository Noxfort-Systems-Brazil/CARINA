// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

import (
	"testing"

	"carina/src_go/pkg/manager"
)

type recordingApplier struct {
	lastID     string
	lastAction map[string]interface{}
}

func (r *recordingApplier) ApplyAction(intersectionID string, actionData map[string]interface{}) (bool, error) {
	r.lastID = intersectionID
	r.lastAction = actionData
	return true, nil
}

func TestExecutePreemptionForwardsStageIdxZeroAndStageCodes(t *testing.T) {
	rec := &recordingApplier{}
	d := &Dispatcher{mgr: rec}

	zeroIdx := 0
	cmd := PreemptionCommand{
		IntersectionID: "J1",
		ActionType:     "activate_preempt",
		TargetStage:    1,
		StageIdx:       &zeroIdx,
		StageCodes:     map[int]string{0: "GGrr", 2: "rrGG"},
		VehicleID:      "AMB-01",
	}

	res := d.ExecutePreemption(cmd)
	if !res.Success || res.ActionExecuted != "HOLD_STAGE_1" {
		t.Fatalf("Expected success HOLD_STAGE_1, got %+v", res)
	}
	if rec.lastID != "J1" {
		t.Fatalf("Expected intersection J1, got %s", rec.lastID)
	}
	if gotIdx, ok := rec.lastAction["stage_idx"].(int); !ok || gotIdx != 0 {
		t.Fatalf("Expected stage_idx=0 in actionData, got %v (%T)", rec.lastAction["stage_idx"], rec.lastAction["stage_idx"])
	}
	if codes, ok := rec.lastAction["stage_codes"].(map[int]string); !ok || codes[0] != "GGrr" || codes[2] != "rrGG" {
		t.Fatalf("Expected stage_codes in actionData, got %v", rec.lastAction["stage_codes"])
	}

	rel := d.ExecutePreemption(PreemptionCommand{
		IntersectionID: "J1",
		ActionType:     "release_preempt",
	})
	if !rel.Success || rel.ActionExecuted != "RELEASE_HOLD" || rec.lastAction["action_type"] != "release_hold" {
		t.Fatalf("Expected release_hold on release_preempt, got %+v action=%v", rel, rec.lastAction)
	}
}

func TestExecutePreemptionNilManagerReturnsError(t *testing.T) {
	var nilMgr *manager.HardwareManager
	d := NewDispatcher(nilMgr)
	res := d.ExecutePreemption(PreemptionCommand{IntersectionID: "J1", ActionType: "activate_preempt"})
	if res.Success || res.Error == "" {
		t.Fatalf("Expected error when manager is nil, got %+v", res)
	}
}
