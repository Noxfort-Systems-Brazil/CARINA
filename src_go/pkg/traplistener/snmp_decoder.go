// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package traplistener

import (
	"fmt"
	"io"
	"log"
	"strings"
	"time"
	"unicode"

	"github.com/gosnmp/gosnmp"
)

const snmpTrapOIDKey = "1.3.6.1.6.3.1.1.4.1.0"

// decodeBinarySNMPPacket decodes raw ASN.1/BER SNMPv1, SNMPv2c or SNMPv3 Trap/Inform packets.
func (l *Listener) decodeBinarySNMPPacket(raw []byte, srcIP string) (TrapEvent, bool) {
	if len(raw) < 3 || raw[0] != 0x30 {
		return TrapEvent{}, false
	}

	decoder := &gosnmp.GoSNMP{
		Target:    srcIP,
		Port:      uint16(l.Port),
		Version:   gosnmp.Version2c,
		Transport: "udp",
		MaxOids:   gosnmp.MaxOids,
		Logger:    gosnmp.NewLogger(log.New(io.Discard, "", 0)),
	}

	pkt, err := decoder.SnmpDecodePacket(raw)
	if err != nil || pkt == nil {
		return TrapEvent{}, false
	}

	if pkt.PDUType != gosnmp.Trap && pkt.PDUType != gosnmp.SNMPv2Trap && pkt.PDUType != gosnmp.InformRequest {
		return TrapEvent{}, false
	}

	trapOID, varbindParts := extractTrapOIDAndVarbinds(pkt)
	level, summary := classifySNMPTrap(trapOID, pkt.GenericTrap, varbindParts)
	details := summary
	if len(varbindParts) > 0 {
		details = fmt.Sprintf("%s [%s]", summary, strings.Join(varbindParts, "; "))
	}

	intersectionID := l.resolveIntersectionID(srcIP, pkt.AgentAddress)
	return TrapEvent{
		Type:           "event",
		EventType:      "trap",
		IntersectionID: intersectionID,
		OID:            trapOID,
		Level:          level,
		Category:       "HARDWARE",
		Details:        details,
		SourceIP:       srcIP,
		Timestamp:      time.Now().UTC().Format(time.RFC3339),
	}, true
}

func (l *Listener) resolveIntersectionID(srcIP, agentAddr string) string {
	if l.GetIntersectionByIP != nil {
		if id := l.GetIntersectionByIP(srcIP); id != "" {
			return id
		}
		trimmedAgent := strings.TrimSpace(agentAddr)
		if trimmedAgent != "" && trimmedAgent != srcIP {
			if id := l.GetIntersectionByIP(trimmedAgent); id != "" {
				return id
			}
		}
	}
	return "DESCONHECIDO"
}

func extractTrapOIDAndVarbinds(pkt *gosnmp.SnmpPacket) (string, []string) {
	trapOID := ""
	if pkt.PDUType == gosnmp.Trap {
		trapOID = resolveV1TrapOID(pkt.Enterprise, pkt.GenericTrap, pkt.SpecificTrap)
	}

	var varbinds []string
	for _, v := range pkt.Variables {
		cleanName := strings.TrimPrefix(strings.TrimSpace(v.Name), ".")
		valStr := formatPDUValue(v)
		if cleanName == snmpTrapOIDKey && valStr != "" {
			trapOID = strings.TrimPrefix(valStr, ".")
			continue
		}
		if cleanName == "1.3.6.1.2.1.1.3.0" {
			continue // sysUpTime.0 does not add fault context when summarized alongside trap OID
		}
		varbinds = append(varbinds, fmt.Sprintf("%s=%s", cleanName, valStr))
	}

	if trapOID == "" {
		trapOID = "1.3.6.1.4.1.2825.4.1"
	}
	return trapOID, varbinds
}

func resolveV1TrapOID(enterprise string, genericTrap, specificTrap int) string {
	switch genericTrap {
	case 0, 1, 2, 3, 4, 5:
		return fmt.Sprintf("1.3.6.1.6.3.1.1.5.%d", genericTrap+1)
	default:
		cleanEnt := strings.TrimPrefix(strings.TrimSpace(enterprise), ".")
		if cleanEnt == "" {
			return fmt.Sprintf("1.3.6.1.4.1.2825.0.%d", specificTrap)
		}
		return fmt.Sprintf("%s.0.%d", cleanEnt, specificTrap)
	}
}

func formatPDUValue(pdu gosnmp.SnmpPDU) string {
	switch val := pdu.Value.(type) {
	case []byte:
		text := strings.TrimSpace(string(val))
		if isPrintableASCII(text) && text != "" {
			return text
		}
		return fmt.Sprintf("0x%x", val)
	case string:
		return strings.TrimPrefix(strings.TrimSpace(val), ".")
	default:
		return fmt.Sprintf("%v", val)
	}
}

func isPrintableASCII(s string) bool {
	for _, r := range s {
		if r > unicode.MaxASCII || !unicode.IsPrint(r) {
			return false
		}
	}
	return true
}

func classifySNMPTrap(trapOID string, genericTrap int, varbinds []string) (string, string) {
	switch trapOID {
	case "1.3.6.1.6.3.1.1.5.1":
		return "WARNING", "SNMP coldStart: controlador reinicializado"
	case "1.3.6.1.6.3.1.1.5.2":
		return "INFO", "SNMP warmStart: reinicialização branda do controlador"
	case "1.3.6.1.6.3.1.1.5.3":
		return "CRITICAL", "SNMP linkDown: perda de enlace ou interface offline"
	case "1.3.6.1.6.3.1.1.5.4":
		return "INFO", "SNMP linkUp: enlace de comunicação restabelecido"
	case "1.3.6.1.6.3.1.1.5.5":
		return "CRITICAL", "SNMP authenticationFailure: falha de autenticação SNMP"
	}

	joined := strings.ToLower(trapOID + " " + strings.Join(varbinds, " "))
	level := "WARNING"
	if strings.Contains(joined, "conflict") ||
		strings.Contains(joined, "mmu") ||
		strings.Contains(joined, "flash") ||
		strings.Contains(joined, "fail") ||
		strings.Contains(joined, "critical") ||
		strings.Contains(joined, "fault") {
		level = "CRITICAL"
	} else if genericTrap == 1 || genericTrap == 3 {
		level = "INFO"
	}

	switch {
	case strings.HasPrefix(trapOID, "1.3.6.1.4.1.1206."):
		return level, fmt.Sprintf("Trap NTCIP (%s)", trapOID)
	case strings.HasPrefix(trapOID, "1.3.6.1.4.1.13267."), strings.HasPrefix(trapOID, "1.3.6.1.4.1.2825."):
		return level, fmt.Sprintf("Trap UTMC (%s)", trapOID)
	default:
		return level, fmt.Sprintf("SNMP Trap (%s)", trapOID)
	}
}
