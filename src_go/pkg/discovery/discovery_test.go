// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package discovery

import (
	"testing"

	"carina/src_go/pkg/snmp"
	"carina/src_go/pkg/snmptest"
	"github.com/gosnmp/gosnmp"
)

func TestExtractBrandAndModel(t *testing.T) {
	cases := []struct {
		input         string
		expectedBrand string
		expectedModel string
	}{
		{
			input:         "Siemens Traffic Controller ST950 ELV",
			expectedBrand: "Siemens",
			expectedModel: "ST950",
		},
		{
			input:         "SWARCO ITC-2 M3000 controller",
			expectedBrand: "Swarco",
			expectedModel: "M3000",
		},
		{
			input:         "Econolite ASC/3 NTCIP Controller",
			expectedBrand: "Econolite",
			expectedModel: "ASC/3",
		},
		{
			input:         "",
			expectedBrand: "Não informado",
			expectedModel: "Não informado",
		},
	}

	for _, c := range cases {
		brand, model := ExtractBrandAndModel(c.input)
		if brand != c.expectedBrand {
			t.Errorf("Para '%s': esperado brand '%s', obteve '%s'", c.input, c.expectedBrand, brand)
		}
		if model != c.expectedModel {
			t.Errorf("Para '%s': esperado model '%s', obteve '%s'", c.input, c.expectedModel, model)
		}
	}
}

func TestDiscoverAndCreateWithConfigProbesBitmask(t *testing.T) {
	// 1. Generic sysDescr + NTCIP binary OCTET STRING bitmask probe -> NTCIP 1202
	ntcipAgent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		oidSysDescr:   {Type: gosnmp.OctetString, Value: []byte("Generic Traffic Controller")},
		oidProbeNtcip: {Type: gosnmp.OctetString, Value: []byte{0x04}},
	})
	drvNtcip, err := DiscoverAndCreateWithConfig(
		"127.0.0.1",
		ntcipAgent.Port,
		snmp.SNMPConfig{Version: "2c", Community: "public"},
		"tl_ntcip",
		[]int{0, 1, 2, 3},
		"",
	)
	if err != nil {
		t.Fatalf("DiscoverAndCreateWithConfig NTCIP falhou: %v", err)
	}
	defer drvNtcip.Shutdown()
	if proto := drvNtcip.GetProtocolName(); proto != "NTCIP 1202" {
		t.Errorf("Esperado protocolo NTCIP 1202, obteve %s", proto)
	}

	// 2. Fallback to UTMC2 when NTCIP probe is absent and UTMC responds with binary OCTET STRING
	utmcAgent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		oidSysDescr:  {Type: gosnmp.OctetString, Value: []byte("Mock Field Unit")},
		oidProbeUtmc: {Type: gosnmp.OctetString, Value: []byte{0x01}},
	})
	drvUtmc, err := DiscoverAndCreateWithConfig(
		"127.0.0.1",
		utmcAgent.Port,
		snmp.SNMPConfig{Version: "2c", Community: "public"},
		"tl_utmc",
		[]int{0, 1, 2, 3},
		"",
	)
	if err != nil {
		t.Fatalf("DiscoverAndCreateWithConfig UTMC falhou: %v", err)
	}
	defer drvUtmc.Shutdown()
	if proto := drvUtmc.GetProtocolName(); proto != "UTMC2" {
		t.Errorf("Esperado protocolo UTMC2, obteve %s", proto)
	}
}
