// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

// GetTelemetry queries green, yellow, red, vehicle call, and pedestrian call OIDs configured in JSON.
func (d *Driver) GetTelemetry() (map[string]interface{}, error) {
	d.mu.Lock()
	currStage := d.CurrentStage
	brand := d.Brand
	model := d.Model
	d.mu.Unlock()

	telemetry := map[string]interface{}{
		"protocol":         "NTCIP 1202",
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

	greens, errG := d.Client.GetBitmask(d.Config.Telemetry.StatusGreens)
	yellows, errY := d.Client.GetBitmask(d.Config.Telemetry.StatusYellows)
	reds, errR := d.Client.GetBitmask(d.Config.Telemetry.StatusReds)
	peds, errP := d.Client.GetBitmask(d.Config.Telemetry.StatusPedCalls)

	if errG == nil {
		telemetry["active_greens"] = greens
		telemetry["status"] = "online"
	}
	if errY == nil {
		telemetry["active_yellows"] = yellows
		telemetry["status"] = "online"
	}
	if errR == nil {
		telemetry["active_reds"] = reds
		telemetry["status"] = "online"
	}
	if errP == nil {
		telemetry["active_ped_calls"] = peds
	}
	if d.Config.Telemetry.StatusVehCalls != "" {
		if vehCalls, errV := d.Client.GetBitmask(d.Config.Telemetry.StatusVehCalls); errV == nil {
			telemetry["active_veh_calls"] = vehCalls
		}
	}

	if errG != nil && errY != nil && errR != nil {
		telemetry["status"] = "offline"
	}

	return telemetry, nil
}
