// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

import (
	"testing"
)

func TestUtmcStageMask(t *testing.T) {
	d := NewDriver("127.0.0.1", 161, "tl_utmc", "public", []int{0, 1, 2})

	mask0 := d.ConvertStageToHardwareMask(0, []int{0, 1, 2}, nil)
	if mask0 != 1 {
		t.Errorf("Esperado 1 (1<<0) para stage_idx 0, obteve %d", mask0)
	}

	mask2 := d.ConvertStageToHardwareMask(2, []int{0, 1, 2}, nil)
	if mask2 != 4 {
		t.Errorf("Esperado 4 (1<<2) para stage_idx 2, obteve %d", mask2)
	}
}
