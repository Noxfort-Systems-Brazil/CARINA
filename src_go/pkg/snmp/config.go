// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package snmp

import (
	"fmt"
	"strings"
	"time"

	"github.com/gosnmp/gosnmp"
)

// SNMPConfig defines SNMPv2c or SNMPv3 (USM) connection and security parameters.
type SNMPConfig struct {
	Version        string `json:"snmp_version,omitempty"`   // "2c" (default) or "3"
	Community      string `json:"community,omitempty"`      // SNMPv2c community
	SecurityLevel  string `json:"security_level,omitempty"` // "NoAuthNoPriv", "AuthNoPriv", "AuthPriv"
	Username       string `json:"username,omitempty"`
	AuthProtocol   string `json:"auth_protocol,omitempty"` // "MD5", "SHA", "SHA256", "SHA512"
	AuthPassphrase string `json:"auth_passphrase,omitempty"`
	PrivProtocol   string `json:"priv_protocol,omitempty"` // "DES", "AES", "AES192", "AES256"
	PrivPassphrase string `json:"priv_passphrase,omitempty"`
}

// Normalized returns a copy with normalized defaults while keeping v2c backward compatibility.
func (c SNMPConfig) Normalized() SNMPConfig {
	out := c
	out.Version = strings.TrimSpace(strings.ToLower(out.Version))
	if out.Version == "" || out.Version == "v2c" || out.Version == "2" {
		out.Version = "2c"
	}
	if strings.TrimPrefix(out.Version, "v") == "3" {
		out.Version = "3"
	}
	if out.Version != "3" {
		out.Version = "2c"
		if out.Community == "" {
			out.Community = "public"
		}
	}
	return out
}

func parseAuthProtocol(name string) (gosnmp.SnmpV3AuthProtocol, error) {
	switch strings.ToUpper(strings.TrimSpace(name)) {
	case "", "NONE", "NOAUTH":
		return gosnmp.NoAuth, nil
	case "MD5":
		return gosnmp.MD5, nil
	case "SHA", "SHA1":
		return gosnmp.SHA, nil
	case "SHA224":
		return gosnmp.SHA224, nil
	case "SHA256":
		return gosnmp.SHA256, nil
	case "SHA384":
		return gosnmp.SHA384, nil
	case "SHA512":
		return gosnmp.SHA512, nil
	default:
		return gosnmp.NoAuth, fmt.Errorf("unsupported SNMPv3 auth protocol: %s", name)
	}
}

func parsePrivProtocol(name string) (gosnmp.SnmpV3PrivProtocol, error) {
	switch strings.ToUpper(strings.TrimSpace(name)) {
	case "", "NONE", "NOPRIV":
		return gosnmp.NoPriv, nil
	case "DES":
		return gosnmp.DES, nil
	case "AES", "AES128":
		return gosnmp.AES, nil
	case "AES192":
		return gosnmp.AES192, nil
	case "AES256":
		return gosnmp.AES256, nil
	case "AES192C":
		return gosnmp.AES192C, nil
	case "AES256C":
		return gosnmp.AES256C, nil
	default:
		return gosnmp.NoPriv, fmt.Errorf("unsupported SNMPv3 priv protocol: %s", name)
	}
}

func parseSecurityLevel(name string, auth gosnmp.SnmpV3AuthProtocol, priv gosnmp.SnmpV3PrivProtocol) (gosnmp.SnmpV3MsgFlags, error) {
	switch strings.ToUpper(strings.ReplaceAll(strings.TrimSpace(name), "_", "")) {
	case "NOAUTHNOPRIV":
		return gosnmp.NoAuthNoPriv, nil
	case "AUTHNOPRIV":
		return gosnmp.AuthNoPriv, nil
	case "AUTHPRIV":
		return gosnmp.AuthPriv, nil
	case "":
		if auth != gosnmp.NoAuth && priv != gosnmp.NoPriv {
			return gosnmp.AuthPriv, nil
		}
		if auth != gosnmp.NoAuth {
			return gosnmp.AuthNoPriv, nil
		}
		return gosnmp.NoAuthNoPriv, nil
	default:
		return gosnmp.NoAuthNoPriv, fmt.Errorf("unsupported SNMPv3 security level: %s", name)
	}
}

// BuildGoSNMP constructs a gosnmp client from target address and SNMPConfig.
func BuildGoSNMP(ip string, port uint16, cfg SNMPConfig, timeout time.Duration, retries int) (*gosnmp.GoSNMP, error) {
	norm := cfg.Normalized()
	obj := &gosnmp.GoSNMP{
		Target:  ip,
		Port:    port,
		Timeout: timeout,
		Retries: retries,
	}

	if norm.Version == "3" {
		if strings.TrimSpace(norm.Username) == "" {
			return nil, fmt.Errorf("SNMPv3 username is required")
		}
		authProto, err := parseAuthProtocol(norm.AuthProtocol)
		if err != nil {
			return nil, err
		}
		privProto, err := parsePrivProtocol(norm.PrivProtocol)
		if err != nil {
			return nil, err
		}
		flags, err := parseSecurityLevel(norm.SecurityLevel, authProto, privProto)
		if err != nil {
			return nil, err
		}
		if flags >= gosnmp.AuthNoPriv && (authProto == gosnmp.NoAuth || norm.AuthPassphrase == "") {
			return nil, fmt.Errorf("SNMPv3 %v requires auth_protocol and auth_passphrase", flags)
		}
		if flags == gosnmp.AuthPriv && (privProto == gosnmp.NoPriv || norm.PrivPassphrase == "") {
			return nil, fmt.Errorf("SNMPv3 AuthPriv requires priv_protocol and priv_passphrase")
		}

		obj.Version = gosnmp.Version3
		obj.SecurityModel = gosnmp.UserSecurityModel
		obj.MsgFlags = flags
		obj.SecurityParameters = &gosnmp.UsmSecurityParameters{
			UserName:                 norm.Username,
			AuthenticationProtocol:   authProto,
			AuthenticationPassphrase: norm.AuthPassphrase,
			PrivacyProtocol:          privProto,
			PrivacyPassphrase:        norm.PrivPassphrase,
		}
		return obj, nil
	}

	obj.Version = gosnmp.Version2c
	obj.Community = norm.Community
	return obj, nil
}
