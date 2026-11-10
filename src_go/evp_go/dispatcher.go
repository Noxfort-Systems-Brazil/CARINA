// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

import (
	"fmt"
	"log"
	"sync"

	"carina/src_go/pkg/manager"
)

// Dispatcher executes microsecond preemption commands on physical street controllers.
type Dispatcher struct {
	mu  sync.RWMutex
	mgr *manager.HardwareManager
}

// NewDispatcher instantiates the EVP Go dispatcher.
func NewDispatcher(mgr *manager.HardwareManager) *Dispatcher {
	return &Dispatcher{
		mgr: mgr,
	}
}

// ExecutePreemption dispatches activate_preempt or release_preempt to the target intersection.
func (d *Dispatcher) ExecutePreemption(cmd PreemptionCommand) PreemptionResult {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.mgr == nil {
		return PreemptionResult{
			IntersectionID: cmd.IntersectionID,
			Success:        false,
			Error:          "hardware manager is nil",
		}
	}

	switch cmd.ActionType {
	case "activate_preempt":
		log.Printf("[EVP-Go] 🚨 Ativando preempção no semáforo %s para o estágio %d (Viatura: %s)",
			cmd.IntersectionID, cmd.TargetStage, cmd.VehicleID)

		// 1. Apply direct HOLD action on the target stage of the emergency vehicle
		actionData := map[string]interface{}{
			"action_type": "hold",
			"stage":       cmd.TargetStage,
		}
		success, err := d.mgr.ApplyAction(cmd.IntersectionID, actionData)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}

		return PreemptionResult{
			IntersectionID: cmd.IntersectionID,
			Success:        success,
			ActionExecuted: fmt.Sprintf("HOLD_STAGE_%d", cmd.TargetStage),
			Error:          errMsg,
		}

	case "release_preempt":
		log.Printf("[EVP-Go] 🏁 Liberando preempção no semáforo %s (Retorno ao controle nominal)",
			cmd.IntersectionID)

		// Release the hold so the traffic light resumes nominal switching
		actionData := map[string]interface{}{
			"action_type": "release_hold",
		}
		success, err := d.mgr.ApplyAction(cmd.IntersectionID, actionData)
		errMsg := ""
		if err != nil {
			errMsg = err.Error()
		}

		return PreemptionResult{
			IntersectionID: cmd.IntersectionID,
			Success:        success,
			ActionExecuted: "RELEASE_HOLD",
			Error:          errMsg,
		}

	default:
		return PreemptionResult{
			IntersectionID: cmd.IntersectionID,
			Success:        false,
			Error:          fmt.Sprintf("unknown action_type: %s", cmd.ActionType),
		}
	}
}
