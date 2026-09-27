// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

// File: src_go/pkg/ntcip/driver_test.go
// Author: Gabriel Moraes
// Date: September 2026

package ntcip

import (
	"testing"
)

func TestNtcipStageToPhaseMask(t *testing.T) {
	d := NewDriver("127.0.0.1", 161, "tl_test", "public", []int{0, 1, 2, 3})

	// 4 green stages, stage_idx 0 (stage 1) -> 34
	mask0 := d.ConvertStageToHardwareMask(0, []int{0, 1, 2, 3}, nil)
	if mask0 != 34 {
		t.Errorf("Esperado 34 para estágio 1, obteve %d", mask0)
	}

	// stage_idx 1 (stage 2) -> 136
	mask1 := d.ConvertStageToHardwareMask(1, []int{0, 1, 2, 3}, nil)
	if mask1 != 136 {
		t.Errorf("Esperado 136 para estágio 2, obteve %d", mask1)
	}

	// Test dynamic SUMO string mapping
	stageCodes := map[int]string{
		0: "GgOrrOGGO",
		1: "yyyrrrGyy",
	}
	// 5 stages (bypasses 4-stage hardcoded map)
	maskDyn := d.ConvertStageToHardwareMask(0, []int{0, 1, 2, 3, 4}, stageCodes)
	if maskDyn == 0 {
		t.Errorf("Esperado máscara dinâmica maior que 0 para GgOrrOGGO, obteve %d", maskDyn)
	}
}
