// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package configs

import _ "embed"

// DefaultNTCIPJSON contains the embedded standard NTCIP 1202 OID configuration.
//
//go:embed ntcip_oids.json
var DefaultNTCIPJSON []byte

// DefaultUTMCJSON contains the embedded standard UTMC2 OID configuration.
//
//go:embed utmc_oids.json
var DefaultUTMCJSON []byte
