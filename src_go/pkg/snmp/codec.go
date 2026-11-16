// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package snmp

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/gosnmp/gosnmp"
)

func isAllASCIIDigits(b []byte) bool {
	if len(b) == 0 {
		return false
	}
	for _, ch := range b {
		if ch < '0' || ch > '9' {
			return false
		}
	}
	return true
}

func decodeRawBytesLittleEndian(b []byte) int64 {
	var mask uint64
	limit := len(b)
	if limit > 8 {
		limit = 8
	}
	for i := 0; i < limit; i++ {
		mask |= uint64(b[i]) << (8 * i)
	}
	return int64(mask)
}

// DecodeBitmaskPDU converts SNMP INTEGER or OCTET STRING / BitString PDUs into an integer phase bitmask.
func DecodeBitmaskPDU(pdu gosnmp.SnmpPDU, treatSingleByteAsBinary bool) (int64, error) {
	switch pdu.Type {
	case gosnmp.Integer, gosnmp.Counter32, gosnmp.Gauge32, gosnmp.TimeTicks, gosnmp.Counter64, gosnmp.Uinteger32:
		return gosnmp.ToBigInt(pdu.Value).Int64(), nil
	case gosnmp.BitString:
		if rawBytes, ok := pdu.Value.([]byte); ok {
			return decodeRawBytesLittleEndian(rawBytes), nil
		}
		return 0, fmt.Errorf("invalid BitString value %T", pdu.Value)
	case gosnmp.OctetString:
		rawBytes, ok := pdu.Value.([]byte)
		if !ok {
			s := strings.TrimSpace(fmt.Sprintf("%v", pdu.Value))
			return strconv.ParseInt(s, 10, 64)
		}
		if len(rawBytes) == 0 {
			return 0, nil
		}
		if len(rawBytes) == 1 && treatSingleByteAsBinary {
			return int64(rawBytes[0]), nil
		}
		if isAllASCIIDigits(rawBytes) {
			if parsed, err := strconv.ParseInt(string(rawBytes), 10, 64); err == nil {
				return parsed, nil
			}
		}
		return decodeRawBytesLittleEndian(rawBytes), nil
	default:
		return 0, fmt.Errorf("non-numeric SNMP type %v for OID %s", pdu.Type, pdu.Name)
	}
}

func decodeGenericPDUValue(pdu gosnmp.SnmpPDU) interface{} {
	switch pdu.Type {
	case gosnmp.OctetString, gosnmp.BitString:
		if rawBytes, ok := pdu.Value.([]byte); ok {
			return string(rawBytes)
		}
		return fmt.Sprintf("%v", pdu.Value)
	case gosnmp.Integer, gosnmp.Counter32, gosnmp.Gauge32, gosnmp.TimeTicks, gosnmp.Counter64, gosnmp.Uinteger32:
		return gosnmp.ToBigInt(pdu.Value).Int64()
	default:
		return pdu.Value
	}
}

func buildSetPDU(oid string, value interface{}) (gosnmp.SnmpPDU, error) {
	pdu := gosnmp.SnmpPDU{Name: oid}
	switch v := value.(type) {
	case int:
		pdu.Type = gosnmp.Integer
		pdu.Value = v
	case int32:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case int64:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case float64:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case string:
		pdu.Type = gosnmp.OctetString
		pdu.Value = []byte(v)
	case []byte:
		pdu.Type = gosnmp.OctetString
		pdu.Value = v
	default:
		return gosnmp.SnmpPDU{}, fmt.Errorf("tipo não suportado para SNMP SET: %T", value)
	}
	return pdu, nil
}
