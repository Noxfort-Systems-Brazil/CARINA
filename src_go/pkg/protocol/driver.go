// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Noxfort Systems
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

// File: src_go/pkg/protocol/driver.go
// Author: Gabriel Moraes
// Date: September 2026

package protocol

// TrafficDriver defines the common interface for all traffic light controllers (NTCIP 1202 and UTMC2).
type TrafficDriver interface {
	GetProtocolName() string
	ApplyAction(actionData map[string]interface{}) (bool, error)
	ApplyLogicalAction(action int, currentStageIdx int, greenStages []int, stageCodes map[int]string) (bool, error)
	ApplyDecision(action string) (bool, error)
	GetTelemetry() (map[string]interface{}, error)
	SendHeartbeatPulse() (bool, error)
	ReleaseControl() (bool, error)
	GetBrand() string
	GetModel() string
	GetSysDescr() string
	SetMetadata(brand, model, sysDescr string)
	Shutdown()
}
