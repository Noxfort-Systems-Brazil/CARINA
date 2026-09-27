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

// File: src_go/pkg/utmc/telemetry.go
// Author: Gabriel Moraes
// Date: September 2026

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
