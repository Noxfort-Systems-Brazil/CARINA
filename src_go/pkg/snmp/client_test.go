// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package snmp

import (
	"testing"
	"time"

	"github.com/gosnmp/gosnmp"
)

func TestBuildGoSNMP_V2cDefault(t *testing.T) {
	obj, err := BuildGoSNMP("127.0.0.1", 161, SNMPConfig{}, 2*time.Second, 1)
	if err != nil {
		t.Fatalf("unexpected error building v2c GoSNMP: %v", err)
	}
	if obj.Version != gosnmp.Version2c {
		t.Errorf("expected Version2c, got %v", obj.Version)
	}
	if obj.Community != "public" {
		t.Errorf("expected default community 'public', got %q", obj.Community)
	}
}

func TestBuildGoSNMP_V3AuthPrivAndValidation(t *testing.T) {
	obj, err := BuildGoSNMP("10.0.0.10", 161, SNMPConfig{
		Version:        "3",
		Username:       "carina_op",
		SecurityLevel:  "AuthPriv",
		AuthProtocol:   "SHA256",
		AuthPassphrase: "auth-secret-passphrase",
		PrivProtocol:   "AES",
		PrivPassphrase: "priv-secret-passphrase",
	}, 2*time.Second, 1)
	if err != nil {
		t.Fatalf("unexpected error building v3 AuthPriv GoSNMP: %v", err)
	}
	if obj.Version != gosnmp.Version3 || obj.MsgFlags != gosnmp.AuthPriv {
		t.Errorf("expected Version3 AuthPriv, got version=%v flags=%v", obj.Version, obj.MsgFlags)
	}
	usm, ok := obj.SecurityParameters.(*gosnmp.UsmSecurityParameters)
	if !ok {
		t.Fatalf("expected UsmSecurityParameters, got %T", obj.SecurityParameters)
	}
	if usm.AuthenticationProtocol != gosnmp.SHA256 || usm.PrivacyProtocol != gosnmp.AES {
		t.Errorf("unexpected auth/priv protocols: %v / %v", usm.AuthenticationProtocol, usm.PrivacyProtocol)
	}

	// Missing passphrases must fail validation explicitly
	if _, err := BuildGoSNMP("10.0.0.10", 161, SNMPConfig{
		Version:       "3",
		Username:      "carina_op",
		SecurityLevel: "AuthPriv",
		AuthProtocol:  "SHA",
		PrivProtocol:  "AES",
	}, 2*time.Second, 1); err == nil {
		t.Errorf("expected error when AuthPriv passphrases are empty")
	}
}

func TestDecodeBitmaskPDU(t *testing.T) {
	// 1. Standard integer bitmask
	v, err := DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.Integer, Value: 34}, true)
	if err != nil || v != 34 {
		t.Errorf("Integer bitmask failed: val=%d err=%v", v, err)
	}

	// 2. Single-byte raw OCTET STRING bitmask (NTCIP binary bitmap, even if byte overlaps ASCII digit 0x31='1'=49)
	v, err = DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.OctetString, Value: []byte{0x22}}, true)
	if err != nil || v != 34 {
		t.Errorf("Single binary byte OctetString(0x22) failed: val=%d err=%v", v, err)
	}
	v, err = DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.OctetString, Value: []byte{0x31}}, true)
	if err != nil || v != 49 {
		t.Errorf("Single binary byte OctetString(0x31) in GetBitmask should be 49, got val=%d err=%v", v, err)
	}

	// 3. GetInt preserves single-byte ASCII parsing compatibility
	v, err = DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.OctetString, Value: []byte("2")}, false)
	if err != nil || v != 2 {
		t.Errorf("ASCII decimal OctetString in GetInt failed: val=%d err=%v", v, err)
	}

	// 4. Multi-byte ASCII decimal string
	v, err = DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.OctetString, Value: []byte("136")}, true)
	if err != nil || v != 136 {
		t.Errorf("ASCII decimal '136' failed: val=%d err=%v", v, err)
	}

	// 5. Multi-byte raw binary OctetString (16-phase controller: group 1=0x05, group 2=0x02)
	v, err = DecodeBitmaskPDU(gosnmp.SnmpPDU{Type: gosnmp.OctetString, Value: []byte{0x05, 0x02}}, true)
	if err != nil || v != (0x05|(0x02<<8)) {
		t.Errorf("Multi-byte raw binary OctetString failed: val=%d err=%v", v, err)
	}
}
