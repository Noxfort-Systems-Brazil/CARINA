// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package manager

import (
	"testing"

	"carina/src_go/pkg/snmp"
	"carina/src_go/pkg/snmptest"
	"github.com/gosnmp/gosnmp"
)

func TestExplicitProtocolConnectProbesAndFailsafeResume(t *testing.T) {
	mgr := NewHardwareManager(0, nil)

	// Explicit NTCIP connection to unreachable closed port must fail fast via Probe()
	_, err := mgr.ConnectWithSNMPConfig(
		"tl_dead",
		"127.0.0.1",
		1,
		snmp.SNMPConfig{Version: "2c", Community: "public"},
		"NTCIP 1202",
		[]int{0, 1},
		"",
	)
	if err == nil {
		t.Fatalf("Expected explicit NTCIP connection to unreachable port 1 to fail probe")
	}

	agent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		"1.3.6.1.2.1.1.1.0":                {Type: gosnmp.OctetString, Value: []byte("Siemens ST900 NTCIP")},
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1": {Type: gosnmp.OctetString, Value: []byte{0x05}},
	})

	info, err := mgr.ConnectWithSNMPConfig(
		"tl_live",
		"127.0.0.1",
		agent.Port,
		snmp.SNMPConfig{Version: "2c", Community: "public"},
		"NTCIP 1202",
		[]int{0, 1},
		"",
	)
	if err != nil {
		t.Fatalf("Expected explicit NTCIP connection to mock agent to succeed: %v", err)
	}
	if info["brand"] != "Siemens" || info["protocol"] != "NTCIP 1202" {
		t.Errorf("Unexpected connection metadata: %+v", info)
	}

	// Emergency release pauses heartbeats and releases control while retaining driver for recovery
	mgr.EmergencyReleaseControlAll()
	if len(mgr.drivers) != 1 || len(mgr.heartbeats) != 1 {
		t.Fatalf("Expected EmergencyReleaseControlAll to preserve driver/heartbeat entries for recovery")
	}

	// Re-arm control via hold + resume_control_all restarts heartbeats cleanly
	ok, err := mgr.ApplyAction("tl_live", map[string]interface{}{"action_type": "hold", "stage": 1})
	if err != nil || !ok {
		t.Fatalf("Expected hold after recovery to succeed: ok=%v err=%v", ok, err)
	}
	if resumed := mgr.ResumeControlAll(); resumed != 1 {
		t.Errorf("Expected ResumeControlAll to resume 1 heartbeat, got %d", resumed)
	}

	// ShutdownAll permanently removes drivers and stops heartbeats
	mgr.ShutdownAll()
	if len(mgr.drivers) != 0 || len(mgr.heartbeats) != 0 {
		t.Errorf("Expected ShutdownAll to clear all drivers and heartbeats")
	}
}
