// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

// GetTelemetry queries active stage status, leaving (yellow), vehicle demand, and pedestrian demand OIDs.
func (d *Driver) GetTelemetry() (map[string]interface{}, error) {
	d.mu.Lock()
	currStage := d.CurrentStage
	brand := d.Brand
	model := d.Model
	d.mu.Unlock()

	telemetry := map[string]interface{}{
		"protocol":         "UTMC2",
		"status":           "unknown",
		"active_greens":    int64(0),
		"active_yellows":   int64(0),
		"active_reds":      int64(0),
		"active_veh_calls": int64(0),
		"active_ped_calls": int64(0),
		"brand":            brand,
		"model":            model,
		"intersection_id":  d.IntersectionID,
		"current_stage":    currStage,
	}

	active, errA := d.Client.GetBitmask(d.Config.Telemetry.StatusActive)
	leaving, errL := d.Client.GetBitmask(d.Config.Telemetry.StatusLeaving)
	ped, errP := d.Client.GetBitmask(d.Config.Telemetry.StatusPedDemand)

	if errA == nil {
		telemetry["active_greens"] = active
		telemetry["status"] = "online"
	}
	if errL == nil {
		telemetry["active_yellows"] = leaving
		telemetry["status"] = "online"
	}
	if errP == nil {
		telemetry["active_ped_calls"] = ped
	}
	if d.Config.Telemetry.StatusDemand != "" {
		if demand, errD := d.Client.GetBitmask(d.Config.Telemetry.StatusDemand); errD == nil {
			telemetry["active_veh_calls"] = demand
		}
	}

	if errA != nil && errL != nil {
		telemetry["status"] = "offline"
	}

	return telemetry, nil
}
