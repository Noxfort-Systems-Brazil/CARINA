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

// File: src_go/pkg/utmc/driver.go
// Author: Gabriel Moraes
// Date: September 2026

package utmc

import (
	"log"

	"carina/src_go/pkg/protocol"
	"carina/src_go/pkg/snmp"
)

// Driver implements the UTMC2 protocol for traffic signal control based on JSON configuration.
// Orchestrates execution by delegating mapping to stage_mapper.go and action execution to action_executor.go.
type Driver struct {
	IntersectionID  string
	IPAddress       string
	Port            int
	Community       string
	Brand           string
	Model           string
	SysDescr        string
	GreenStages     []int
	Config          *Config
	CurrentStage    int
	Client          *snmp.Client
	StopHeartbeatCb func()
}

var _ protocol.TrafficDriver = (*Driver)(nil)

// NewDriver instantiates a UTMC2 driver loading the JSON configuration (embedded or from disk).
func NewDriver(ip string, port int, intersectionID string, community string, greenStages []int, configPaths ...string) *Driver {
	if community == "" {
		community = "public"
	}

	var customPath string
	if len(configPaths) > 0 {
		customPath = configPaths[0]
	}

	cfg, err := LoadConfig(customPath)
	if err != nil {
		log.Printf("[UTMC Driver %s] Error loading configuration (%v), initializing default.", intersectionID, err)
		cfg = &Config{}
	}

	return &Driver{
		IntersectionID: intersectionID,
		IPAddress:      ip,
		Port:           port,
		Community:      community,
		Brand:          "Não informado",
		Model:          "Não informado",
		GreenStages:    greenStages,
		Config:         cfg,
		CurrentStage:   1,
		Client:         snmp.NewClient(ip, port, community, 2, 1),
	}
}

func (d *Driver) GetProtocolName() string {
	return "UTMC2"
}

func (d *Driver) GetBrand() string {
	return d.Brand
}

func (d *Driver) GetModel() string {
	return d.Model
}

func (d *Driver) GetSysDescr() string {
	return d.SysDescr
}

func (d *Driver) SetMetadata(brand, model, sysDescr string) {
	d.Brand = brand
	d.Model = model
	d.SysDescr = sysDescr
}

// SendHeartbeatPulse sends the UTMC watchdog pulse.
func (d *Driver) SendHeartbeatPulse() (bool, error) {
	err := d.Client.Set(d.Config.System.Watchdog, 1)
	return err == nil, err
}

// ReleaseControl releases all remote commands returning the controller to its local plan.
func (d *Driver) ReleaseControl() (bool, error) {
	_ = d.Client.Set(d.Config.StageControl.Hold, 0)
	_ = d.Client.Set(d.Config.StageControl.ForceOff, 0)
	_ = d.Client.Set(d.Config.StageControl.Omit, 0)
	_ = d.Client.Set(d.Config.System.Flash, 0)
	_ = d.Client.Set(d.Config.System.Dark, 0)
	return true, nil
}

// Shutdown gracefully terminates the network connection.
func (d *Driver) Shutdown() {
	_, _ = d.ReleaseControl()
	d.Client.Close()
}
