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

// File: src_go/pkg/traplistener/parser.go
// Author: Gabriel Moraes
// Date: September 2026

package traplistener

import (
	"regexp"
	"strings"
	"time"
)

var (
	// TRAP|<INTERSECTION_ID>|<OID>|<LEVEL>|[<CATEGORY>] <MESSAGE>
	regex5Field = regexp.MustCompile(`(?i)TRAP\|([^|]+)\|([^|]+)\|([^|]+)\|\[([^\]]+)\]\s*(.*)`)
	// TRAP|<OID>|<LEVEL>|[<CATEGORY>] <MESSAGE>
	regex4Field = regexp.MustCompile(`(?i)TRAP\|([^|]+)\|([^|]+)\|\[([^\]]+)\]\s*(.*)`)
)

func (l *Listener) parsePayload(rawText string, srcIP string) TrapEvent {
	nowStr := time.Now().UTC().Format(time.RFC3339)
	clean := strings.TrimSpace(rawText)

	// Remove non-printable characters
	var b strings.Builder
	for _, r := range clean {
		if r >= 32 && r != 127 {
			b.WriteRune(r)
		}
	}
	clean = b.String()

	// 1. Standard 5-field format
	if m := regex5Field.FindStringSubmatch(clean); len(m) == 6 {
		intersectionID := strings.TrimSpace(m[1])
		oid := strings.TrimSpace(m[2])
		level := strings.ToUpper(strings.TrimSpace(m[3]))
		rawCat := strings.ToUpper(strings.TrimSpace(m[4]))
		details := strings.TrimSpace(m[5])

		cat := "HARDWARE"
		if strings.Contains(rawCat, "SOFTWARE") {
			cat = "SOFTWARE"
		}
		if level != "INFO" && level != "WARNING" && level != "CRITICAL" {
			level = "CRITICAL"
		}

		return TrapEvent{
			Type:           "event",
			EventType:      "trap",
			IntersectionID: intersectionID,
			OID:            oid,
			Level:          level,
			Category:       cat,
			Details:        details,
			SourceIP:       srcIP,
			Timestamp:      nowStr,
		}
	}

	// 2. Standard 4-field format
	if m := regex4Field.FindStringSubmatch(clean); len(m) == 5 {
		oid := strings.TrimSpace(m[1])
		level := strings.ToUpper(strings.TrimSpace(m[2]))
		rawCat := strings.ToUpper(strings.TrimSpace(m[3]))
		details := strings.TrimSpace(m[4])

		cat := "HARDWARE"
		if strings.Contains(rawCat, "SOFTWARE") {
			cat = "SOFTWARE"
		}
		if level != "INFO" && level != "WARNING" && level != "CRITICAL" {
			level = "CRITICAL"
		}

		intersectionID := "DESCONHECIDO"
		if l.GetIntersectionByIP != nil {
			if id := l.GetIntersectionByIP(srcIP); id != "" {
				intersectionID = id
			}
		}

		return TrapEvent{
			Type:           "event",
			EventType:      "trap",
			IntersectionID: intersectionID,
			OID:            oid,
			Level:          level,
			Category:       cat,
			Details:        details,
			SourceIP:       srcIP,
			Timestamp:      nowStr,
		}
	}

	// Fallback
	intersectionID := "DESCONHECIDO"
	if l.GetIntersectionByIP != nil {
		if id := l.GetIntersectionByIP(srcIP); id != "" {
			intersectionID = id
		}
	}

	return TrapEvent{
		Type:           "event",
		EventType:      "trap",
		IntersectionID: intersectionID,
		OID:            "1.3.6.1.4.1.2825.4.1",
		Level:          "WARNING",
		Category:       "HARDWARE",
		Details:        clean,
		SourceIP:       srcIP,
		Timestamp:      nowStr,
	}
}
