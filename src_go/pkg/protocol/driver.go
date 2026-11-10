// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
