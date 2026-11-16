// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package traplistener

import (
	"fmt"
	"net"
	"testing"
	"time"

	"github.com/gosnmp/gosnmp"
)

func TestParsePayload5Field(t *testing.T) {
	l := NewListener(1620, nil, nil)

	raw := "TRAP|tl_av_paulista|1.3.6.1.4.1.1206.4.2|CRITICAL|[HARDWARE] Falha no grupo focal 1"
	event := l.parsePayload(raw, "192.168.1.50")

	if event.IntersectionID != "tl_av_paulista" {
		t.Errorf("Esperado intersection_id 'tl_av_paulista', obteve '%s'", event.IntersectionID)
	}
	if event.Level != "CRITICAL" {
		t.Errorf("Esperado level 'CRITICAL', obteve '%s'", event.Level)
	}
	if event.Category != "HARDWARE" {
		t.Errorf("Esperado category 'HARDWARE', obteve '%s'", event.Category)
	}
	if event.Details != "Falha no grupo focal 1" {
		t.Errorf("Esperado details 'Falha no grupo focal 1', obteve '%s'", event.Details)
	}
	if event.SourceIP != "192.168.1.50" {
		t.Errorf("Esperado source_ip '192.168.1.50', obteve '%s'", event.SourceIP)
	}
}

func TestParsePayload4Field(t *testing.T) {
	l := NewListener(1620, nil, func(ip string) string {
		if ip == "192.168.1.60" {
			return "tl_ip_resolved"
		}
		return ""
	})

	raw := "TRAP|1.3.6.1.4.1.2825.4.1|WARNING|[SOFTWARE] Loop de detecção com timeout"
	event := l.parsePayload(raw, "192.168.1.60")

	if event.IntersectionID != "tl_ip_resolved" {
		t.Errorf("Esperado intersection_id 'tl_ip_resolved', obteve '%s'", event.IntersectionID)
	}
	if event.Level != "WARNING" {
		t.Errorf("Esperado level 'WARNING', obteve '%s'", event.Level)
	}
	if event.Category != "SOFTWARE" {
		t.Errorf("Esperado category 'SOFTWARE', obteve '%s'", event.Category)
	}
}

func TestDecodeBinarySNMPv2cTrapAndUDP(t *testing.T) {
	pkt := &gosnmp.SnmpPacket{
		Version:   gosnmp.Version2c,
		Community: "public",
		PDUType:   gosnmp.SNMPv2Trap,
		RequestID: 101,
		Variables: []gosnmp.SnmpPDU{
			{Name: "1.3.6.1.2.1.1.3.0", Type: gosnmp.TimeTicks, Value: uint32(12345)},
			{Name: "1.3.6.1.6.3.1.1.4.1.0", Type: gosnmp.ObjectIdentifier, Value: "1.3.6.1.4.1.1206.4.2.1.99"},
			{Name: "1.3.6.1.4.1.1206.4.2.1.1.1", Type: gosnmp.OctetString, Value: []byte("MMU Conflict Flash")},
		},
	}
	raw, err := pkt.MarshalMsg()
	if err != nil {
		t.Fatalf("MarshalMsg SNMPv2c trap falhou: %v", err)
	}

	received := make(chan TrapEvent, 1)
	l := NewListener(0, func(ev TrapEvent) {
		received <- ev
	}, func(ip string) string {
		return "tl_ber_test"
	})

	// Allocate ephemeral free UDP port via net.ListenPacket? Listener uses l.Port, pick free port first
	probe, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
	if err != nil {
		t.Fatalf("Falha ao alocar porta UDP efêmera: %v", err)
	}
	freePort := probe.LocalAddr().(*net.UDPAddr).Port
	_ = probe.Close()

	l.Port = freePort
	if err := l.Start(); err != nil {
		t.Fatalf("Listener.Start falhou: %v", err)
	}
	defer l.Stop()

	conn, err := net.Dial("udp", fmt.Sprintf("127.0.0.1:%d", freePort))
	if err != nil {
		t.Fatalf("UDP Dial falhou: %v", err)
	}
	defer conn.Close()
	if _, err := conn.Write(raw); err != nil {
		t.Fatalf("UDP Write falhou: %v", err)
	}

	select {
	case ev := <-received:
		if ev.IntersectionID != "tl_ber_test" {
			t.Errorf("Esperado tl_ber_test, obteve %s", ev.IntersectionID)
		}
		if ev.OID != "1.3.6.1.4.1.1206.4.2.1.99" {
			t.Errorf("Esperado OID NTCIP, obteve %s", ev.OID)
		}
		if ev.Level != "CRITICAL" {
			t.Errorf("Esperado CRITICAL para MMU Conflict Flash, obteve %s", ev.Level)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Timeout aguardando SNMPv2c Trap via UDP")
	}
}

func TestDecodeBinarySNMPv1Trap(t *testing.T) {
	l := NewListener(1620, nil, func(ip string) string {
		if ip == "10.20.30.40" {
			return "tl_v1_agent"
		}
		return ""
	})

	pkt := &gosnmp.SnmpPacket{
		Version:   gosnmp.Version1,
		Community: "public",
		PDUType:   gosnmp.Trap,
		SnmpTrap: gosnmp.SnmpTrap{
			Enterprise:   "1.3.6.1.4.1.1206",
			AgentAddress: "10.20.30.40",
			GenericTrap:  2, // linkDown
			SpecificTrap: 0,
			Timestamp:    555,
			Variables: []gosnmp.SnmpPDU{
				{Name: "1.3.6.1.2.1.2.2.1.1.1", Type: gosnmp.Integer, Value: 1},
			},
		},
	}
	raw, err := pkt.MarshalMsg()
	if err != nil {
		t.Fatalf("MarshalMsg SNMPv1 trap falhou: %v", err)
	}

	ev := l.parseRawPayload(raw, "127.0.0.1")
	if ev.IntersectionID != "tl_v1_agent" {
		t.Errorf("Esperado tl_v1_agent via AgentAddress fallback, obteve %s", ev.IntersectionID)
	}
	if ev.OID != "1.3.6.1.6.3.1.1.5.3" {
		t.Errorf("Esperado linkDown OID 1.3.6.1.6.3.1.1.5.3, obteve %s", ev.OID)
	}
	if ev.Level != "CRITICAL" {
		t.Errorf("Esperado CRITICAL para linkDown, obteve %s", ev.Level)
	}
}
