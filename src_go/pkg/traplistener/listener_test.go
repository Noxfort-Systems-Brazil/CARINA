// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package traplistener

import (
	"testing"
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
