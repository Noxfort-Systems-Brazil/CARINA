// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
