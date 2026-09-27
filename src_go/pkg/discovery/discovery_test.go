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

// File: src_go/pkg/discovery/discovery_test.go
// Author: Gabriel Moraes
// Date: September 2026

package discovery

import (
	"testing"
)

func TestExtractBrandAndModel(t *testing.T) {
	cases := []struct {
		input         string
		expectedBrand string
		expectedModel string
	}{
		{
			input:         "Siemens Traffic Controller ST950 ELV",
			expectedBrand: "Siemens",
			expectedModel: "ST950",
		},
		{
			input:         "SWARCO ITC-2 M3000 controller",
			expectedBrand: "Swarco",
			expectedModel: "M3000",
		},
		{
			input:         "Econolite ASC/3 NTCIP Controller",
			expectedBrand: "Econolite",
			expectedModel: "ASC/3",
		},
		{
			input:         "",
			expectedBrand: "Não informado",
			expectedModel: "Não informado",
		},
	}

	for _, c := range cases {
		brand, model := ExtractBrandAndModel(c.input)
		if brand != c.expectedBrand {
			t.Errorf("Para '%s': esperado brand '%s', obteve '%s'", c.input, c.expectedBrand, brand)
		}
		if model != c.expectedModel {
			t.Errorf("Para '%s': esperado model '%s', obteve '%s'", c.input, c.expectedModel, model)
		}
	}
}
