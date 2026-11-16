// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package evp_go

// PreemptionCommand represents a high-speed hardware dispatch request.
type PreemptionCommand struct {
	IntersectionID string         `json:"intersection_id"`
	ActionType     string         `json:"action_type"` // "activate_preempt", "release_preempt"
	TargetStage    int            `json:"target_stage"`
	StageIdx       *int           `json:"stage_idx,omitempty"`
	StageCodes     map[int]string `json:"stage_codes,omitempty"`
	VehicleID      string         `json:"vehicle_id,omitempty"`
	Corporation    string         `json:"corporation,omitempty"`
}

// PreemptionResult represents the hardware execution status.
type PreemptionResult struct {
	IntersectionID string `json:"intersection_id"`
	Success        bool   `json:"success"`
	ActionExecuted string `json:"action_executed"`
	Error          string `json:"error,omitempty"`
}
