// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

// GetTelemetry queries green, yellow, red, and pedestrian call OIDs configured in the JSON schema.
func (d *Driver) GetTelemetry() (map[string]interface{}, error) {
	telemetry := map[string]interface{}{
		"protocol":         "NTCIP 1202",
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

	greens, errG := d.Client.GetInt(d.Config.Telemetry.StatusGreens)
	yellows, errY := d.Client.GetInt(d.Config.Telemetry.StatusYellows)
	reds, errR := d.Client.GetInt(d.Config.Telemetry.StatusReds)
	peds, errP := d.Client.GetInt(d.Config.Telemetry.StatusPedCalls)

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

	if errG != nil && errY != nil && errR != nil {
		telemetry["status"] = "offline"
	}

	return telemetry, nil
}
