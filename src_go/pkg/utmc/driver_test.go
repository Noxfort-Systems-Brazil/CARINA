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

// File: src_go/pkg/utmc/driver_test.go
// Author: Gabriel Moraes
// Date: September 2026

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
