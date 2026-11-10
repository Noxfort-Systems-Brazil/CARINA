// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

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
