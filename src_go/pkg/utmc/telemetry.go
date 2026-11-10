// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

// GetTelemetry queries active stage status, leaving (yellow), and pedestrian demand OIDs.
func (d *Driver) GetTelemetry() (map[string]interface{}, error) {
	telemetry := map[string]interface{}{
		"protocol":         "UTMC2",
		"status":           "unknown",
		"active_greens":    int64(0),
		"active_yellows":   int64(0),
		"active_reds":      int64(0),
		"active_ped_calls": int64(0),
		"brand":            d.Brand,
		"model":            d.Model,
		"intersection_id":  d.IntersectionID,
		"current_stage":    d.CurrentStage,
	}

	active, errA := d.Client.GetInt(d.Config.Telemetry.StatusActive)
	leaving, errL := d.Client.GetInt(d.Config.Telemetry.StatusLeaving)
	ped, errP := d.Client.GetInt(d.Config.Telemetry.StatusPedDemand)

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

	if errA != nil && errL != nil {
		telemetry["status"] = "offline"
	}

	return telemetry, nil
}
