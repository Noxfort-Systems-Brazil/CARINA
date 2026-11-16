// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

import (
	"fmt"
	"log"
	"sync"
	"time"

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

	mu            sync.Mutex
	failsafeTimer *time.Timer
	closed        bool
	released      bool
}

var _ protocol.TrafficDriver = (*Driver)(nil)

// NewDriver instantiates a UTMC2 driver using SNMPv2c community credentials.
func NewDriver(ip string, port int, intersectionID string, community string, greenStages []int, configPaths ...string) *Driver {
	return NewDriverWithConfig(ip, port, intersectionID, snmp.SNMPConfig{
		Version:   "2c",
		Community: community,
	}, greenStages, configPaths...)
}

// NewDriverWithConfig instantiates a UTMC2 driver supporting SNMPv2c or SNMPv3 configuration.
func NewDriverWithConfig(
	ip string,
	port int,
	intersectionID string,
	snmpCfg snmp.SNMPConfig,
	greenStages []int,
	configPaths ...string,
) *Driver {
	normCfg := snmpCfg.Normalized()

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
		Community:      normCfg.Community,
		Brand:          "Não informado",
		Model:          "Não informado",
		GreenStages:    greenStages,
		Config:         cfg,
		CurrentStage:   1,
		Client:         snmp.NewClientWithConfig(ip, port, normCfg, 2, 1),
	}
}

func (d *Driver) cancelFailsafeTimer() {
	d.mu.Lock()
	if d.failsafeTimer != nil {
		d.failsafeTimer.Stop()
		d.failsafeTimer = nil
	}
	d.mu.Unlock()
}

func (d *Driver) scheduleOmitClear(delay time.Duration) {
	d.mu.Lock()
	if d.closed {
		d.mu.Unlock()
		return
	}
	if d.failsafeTimer != nil {
		d.failsafeTimer.Stop()
	}
	d.failsafeTimer = time.AfterFunc(delay, func() {
		d.mu.Lock()
		isClosed := d.closed
		cfg := d.Config
		client := d.Client
		d.mu.Unlock()
		if !isClosed && client != nil && cfg != nil && cfg.StageControl.Omit != "" {
			_ = client.Set(cfg.StageControl.Omit, 0)
		}
	})
	d.mu.Unlock()
}

// SetStopHeartbeatCallback stores the callback invoked when ACTIVATE_LOCAL_FIXED_TIME stops the heartbeat.
func (d *Driver) SetStopHeartbeatCallback(fn func()) {
	d.mu.Lock()
	d.StopHeartbeatCb = fn
	d.mu.Unlock()
}

func (d *Driver) getStopHeartbeatCallback() func() {
	d.mu.Lock()
	cb := d.StopHeartbeatCb
	d.mu.Unlock()
	return cb
}

func (d *Driver) clearReleasedFlag() {
	d.mu.Lock()
	d.released = false
	d.mu.Unlock()
}

// Probe verifies SNMP reachability against the controller and extracts sysDescr metadata when available.
func (d *Driver) Probe() error {
	if d.Client == nil || d.Config == nil {
		return fmt.Errorf("UTMC driver not initialized")
	}
	if _, err := d.Client.GetBitmask(d.Config.Telemetry.StatusActive); err != nil {
		return fmt.Errorf("UTMC2 probe failed on %s:%d: %w", d.IPAddress, d.Port, err)
	}
	if d.GetSysDescr() == "" {
		if val, err := d.Client.Get("1.3.6.1.2.1.1.1.0"); err == nil && val != nil {
			sysDescr := fmt.Sprintf("%v", val)
			brand, model := protocol.ExtractBrandAndModel(sysDescr)
			d.SetMetadata(brand, model, sysDescr)
		}
	}
	return nil
}

func (d *Driver) GetProtocolName() string {
	return "UTMC2"
}

func (d *Driver) GetBrand() string {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.Brand
}

func (d *Driver) GetModel() string {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.Model
}

func (d *Driver) GetSysDescr() string {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.SysDescr
}

func (d *Driver) SetMetadata(brand, model, sysDescr string) {
	d.mu.Lock()
	d.Brand = brand
	d.Model = model
	d.SysDescr = sysDescr
	d.mu.Unlock()
}

// SendHeartbeatPulse sends the UTMC watchdog pulse.
func (d *Driver) SendHeartbeatPulse() (bool, error) {
	d.mu.Lock()
	if d.closed {
		d.mu.Unlock()
		return false, fmt.Errorf("UTMC driver closed")
	}
	d.released = false
	d.mu.Unlock()
	err := d.Client.Set(d.Config.System.Watchdog, 1)
	return err == nil, err
}

// ReleaseControl releases all remote commands returning the controller to its local plan.
func (d *Driver) ReleaseControl() (bool, error) {
	d.cancelFailsafeTimer()
	d.mu.Lock()
	if d.released || d.closed {
		d.mu.Unlock()
		return true, nil
	}
	d.released = true
	d.mu.Unlock()
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
	d.CloseTransport()
}

// CloseTransport closes the underlying SNMP socket without emitting ReleaseControl SETs.
func (d *Driver) CloseTransport() {
	d.mu.Lock()
	if d.closed {
		d.mu.Unlock()
		return
	}
	d.closed = true
	if d.failsafeTimer != nil {
		d.failsafeTimer.Stop()
		d.failsafeTimer = nil
	}
	d.mu.Unlock()
	if d.Client != nil {
		d.Client.Close()
	}
}
