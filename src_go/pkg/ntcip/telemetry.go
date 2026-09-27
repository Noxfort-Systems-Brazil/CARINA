// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.

// File: src_go/pkg/ntcip/telemetry.go
// Author: Gabriel Moraes
// Date: September 2026

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
