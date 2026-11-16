// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package discovery

import (
	"fmt"
	"log"
	"strings"

	"carina/src_go/pkg/ntcip"
	"carina/src_go/pkg/protocol"
	"carina/src_go/pkg/snmp"
	"carina/src_go/pkg/utmc"
)

const oidSysDescr = "1.3.6.1.2.1.1.1.0"
const oidProbeNtcip = "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1" // status_greens
const oidProbeUtmc = "1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1"   // status_active

// ExtractBrandAndModel extracts the manufacturer brand and model from sysDescr string.
func ExtractBrandAndModel(sysDescr string) (string, string) {
	return protocol.ExtractBrandAndModel(sysDescr)
}

// DiscoverAndCreate connects using SNMPv2c and auto-detects NTCIP 1202 vs UTMC2.
func DiscoverAndCreate(ip string, port int, community string, intersectionID string, greenStages []int) (protocol.TrafficDriver, error) {
	return DiscoverAndCreateWithConfig(ip, port, snmp.SNMPConfig{
		Version:   "2c",
		Community: community,
	}, intersectionID, greenStages, "")
}

// DiscoverAndCreateWithConfig connects using SNMPv2c/v3 config, runs protocol handshake, and builds the driver.
func DiscoverAndCreateWithConfig(
	ip string,
	port int,
	snmpCfg snmp.SNMPConfig,
	intersectionID string,
	greenStages []int,
	customConfigPath string,
) (protocol.TrafficDriver, error) {
	normCfg := snmpCfg.Normalized()

	log.Printf("[%s:%d] Iniciando descoberta de protocolo (Handshake, SNMPv%s)...", ip, port, normCfg.Version)
	probeClient := snmp.NewClientWithConfig(ip, port, normCfg, 2, 1)
	defer probeClient.Close()

	detectedBrand := "Não informado"
	detectedModel := "Não informado"
	rawSysDescr := ""

	buildNTCIP := func() protocol.TrafficDriver {
		driver := ntcip.NewDriverWithConfig(ip, port, intersectionID, normCfg, greenStages, customConfigPath)
		driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
		return driver
	}
	buildUTMC := func() protocol.TrafficDriver {
		driver := utmc.NewDriverWithConfig(ip, port, intersectionID, normCfg, greenStages, customConfigPath)
		driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
		return driver
	}

	// 1. Query sysDescr directly
	val, err := probeClient.Get(oidSysDescr)
	if err == nil && val != nil {
		rawSysDescr = fmt.Sprintf("%v", val)
		detectedBrand, detectedModel = ExtractBrandAndModel(rawSysDescr)
		descrUpper := strings.ToUpper(rawSysDescr)

		log.Printf("[%s:%d] sysDescr retornado: '%s' (Marca: '%s', Modelo: '%s')", ip, port, rawSysDescr, detectedBrand, detectedModel)

		if strings.Contains(descrUpper, "NTCIP") {
			log.Printf("[%s:%d] Protocolo identificado como NTCIP 1202 via sysDescr.", ip, port)
			return buildNTCIP(), nil
		}
		if strings.Contains(descrUpper, "UTMC") {
			log.Printf("[%s:%d] Protocolo identificado como UTMC2 via sysDescr.", ip, port)
			return buildUTMC(), nil
		}
		log.Printf("[%s:%d] Protocolo não reconhecido no sysDescr. Iniciando probing ativo...", ip, port)
	} else {
		log.Printf("[%s:%d] sysDescr falhou (%v). Iniciando probing ativo...", ip, port, err)
	}

	// 2. NTCIP 1202 active probing (handles both Integer and binary OCTET STRING bitmasks)
	if valNtcip, errNtcip := probeClient.GetBitmask(oidProbeNtcip); errNtcip == nil {
		log.Printf("[%s:%d] Probe bem-sucedido! Protocolo identificado como NTCIP 1202 (greens: %d).", ip, port, valNtcip)
		return buildNTCIP(), nil
	}

	// 3. UTMC2 active probing
	if valUtmc, errUtmc := probeClient.GetBitmask(oidProbeUtmc); errUtmc == nil {
		log.Printf("[%s:%d] Probe bem-sucedido! Protocolo identificado como UTMC2 (active: %d).", ip, port, valUtmc)
		return buildUTMC(), nil
	}

	return nil, fmt.Errorf("nenhum protocolo suportado (NTCIP ou UTMC) respondeu em %s:%d", ip, port)
}
