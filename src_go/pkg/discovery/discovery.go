// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package discovery

import (
	"fmt"
	"log"
	"regexp"
	"strings"

	"carina/src_go/pkg/ntcip"
	"carina/src_go/pkg/protocol"
	"carina/src_go/pkg/snmp"
	"carina/src_go/pkg/utmc"
)

const oidSysDescr = "1.3.6.1.2.1.1.1.0"
const oidProbeNtcip = "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1" // status_greens
const oidProbeUtmc = "1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1"   // status_active

var modelRegex = regexp.MustCompile(`(?i)\b(ST\d{3,4}|M\d{2,3}|ATC[-_ ]?\d{4}|ASC[/-]?\d+|[A-Z]{1,4}[-_]?\d{3,4})\b`)

var knownBrands = []string{
	"SIEMENS", "PEEK", "SWARCO", "ECONOLITE", "DATAPROM", "TRAFFICWARE",
	"MCCAIN", "YUNEX", "COMPASS", "TELVENT", "KAPSCH",
}

// ExtractBrandAndModel extracts the manufacturer brand and model from sysDescr string.
func ExtractBrandAndModel(sysDescr string) (string, string) {
	if sysDescr == "" {
		return "Não informado", "Não informado"
	}

	descrUpper := strings.ToUpper(sysDescr)
	brand := "Não informado"
	for _, b := range knownBrands {
		if strings.Contains(descrUpper, b) {
			brand = strings.Title(strings.ToLower(b))
			break
		}
	}

	match := modelRegex.FindString(sysDescr)
	var model string
	if match != "" {
		model = strings.ToUpper(match)
	} else {
		if len(sysDescr) <= 30 {
			model = sysDescr
		} else {
			model = sysDescr[:30] + "..."
		}
	}

	return brand, model
}

// DiscoverAndCreate connects to the IP and port, executes protocol handshake, and instantiates the matching driver (NTCIP or UTMC2).
func DiscoverAndCreate(ip string, port int, community string, intersectionID string, greenStages []int) (protocol.TrafficDriver, error) {
	if community == "" {
		community = "public"
	}

	log.Printf("[%s:%d] Iniciando descoberta de protocolo (Handshake)...", ip, port)
	probeClient := snmp.NewClient(ip, port, community, 2, 1)
	defer probeClient.Close()

	var detectedBrand = "Não informado"
	var detectedModel = "Não informado"
	var rawSysDescr = ""

	// 1. Query sysDescr directly
	val, err := probeClient.Get(oidSysDescr)
	if err == nil && val != nil {
		rawSysDescr = fmt.Sprintf("%v", val)
		detectedBrand, detectedModel = ExtractBrandAndModel(rawSysDescr)
		descrUpper := strings.ToUpper(rawSysDescr)

		log.Printf("[%s:%d] sysDescr retornado: '%s' (Marca: '%s', Modelo: '%s')", ip, port, rawSysDescr, detectedBrand, detectedModel)

		if strings.Contains(descrUpper, "NTCIP") {
			log.Printf("[%s:%d] Protocolo identificado como NTCIP 1202 via sysDescr.", ip, port)
			driver := ntcip.NewDriver(ip, port, intersectionID, community, greenStages)
			driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
			return driver, nil
		} else if strings.Contains(descrUpper, "UTMC") {
			log.Printf("[%s:%d] Protocolo identificado como UTMC2 via sysDescr.", ip, port)
			driver := utmc.NewDriver(ip, port, intersectionID, community, greenStages)
			driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
			return driver, nil
		}
		log.Printf("[%s:%d] Protocolo não reconhecido no sysDescr. Iniciando probing ativo...", ip, port)
	} else {
		log.Printf("[%s:%d] sysDescr falhou (%v). Iniciando probing ativo...", ip, port, err)
	}

	// 2. NTCIP 1202 active probing
	valNtcip, errNtcip := probeClient.GetInt(oidProbeNtcip)
	if errNtcip == nil {
		log.Printf("[%s:%d] Probe bem-sucedido! Protocolo identificado como NTCIP 1202 (greens: %d).", ip, port, valNtcip)
		driver := ntcip.NewDriver(ip, port, intersectionID, community, greenStages)
		driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
		return driver, nil
	}

	// 3. UTMC2 active probing
	valUtmc, errUtmc := probeClient.GetInt(oidProbeUtmc)
	if errUtmc == nil {
		log.Printf("[%s:%d] Probe bem-sucedido! Protocolo identificado como UTMC2 (active: %d).", ip, port, valUtmc)
		driver := utmc.NewDriver(ip, port, intersectionID, community, greenStages)
		driver.SetMetadata(detectedBrand, detectedModel, rawSysDescr)
		return driver, nil
	}

	return nil, fmt.Errorf("nenhum protocolo suportado (NTCIP ou UTMC) respondeu em %s:%d", ip, port)
}
