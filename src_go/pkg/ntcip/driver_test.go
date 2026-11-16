// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package ntcip

import (
	"testing"
	"time"

	"carina/src_go/pkg/snmptest"
	"github.com/gosnmp/gosnmp"
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

	// Sparse green stages ([0, 3]) -> ordinal 1 maps to StageToPhaseMap[2] = 136 when stageCodes is absent
	maskSparse := d.ConvertStageToHardwareMask(3, []int{0, 3}, nil)
	if maskSparse != 136 {
		t.Errorf("Esperado 136 para estágio esparso 3 em [0, 3], obteve %d", maskSparse)
	}
}

func TestNtcipMockUdpActionsAndTelemetry(t *testing.T) {
	agent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1": {Type: gosnmp.OctetString, Value: []byte{0x05}}, // greens = 5
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1": {Type: gosnmp.Integer, Value: 2},
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1": {Type: gosnmp.Integer, Value: 8},
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1": {Type: gosnmp.OctetString, Value: []byte{0x03}}, // veh_calls = 3
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1": {Type: gosnmp.Integer, Value: 0},
	})

	d := NewDriver("127.0.0.1", agent.Port, "tl_ntcip_test", "public", []int{0, 3})
	defer d.Shutdown()

	tel, err := d.GetTelemetry()
	if err != nil {
		t.Fatalf("GetTelemetry falhou: %v", err)
	}
	if tel["status"] != "online" {
		t.Errorf("Esperado status online, obteve %v", tel["status"])
	}
	if tel["active_greens"] != int64(5) {
		t.Errorf("Esperado active_greens=5 de OCTET STRING binário, obteve %v", tel["active_greens"])
	}
	if tel["active_veh_calls"] != int64(3) {
		t.Errorf("Esperado active_veh_calls=3 de OCTET STRING binário, obteve %v", tel["active_veh_calls"])
	}

	ok, err := d.ApplyAction(map[string]interface{}{
		"action_type": "hold",
		"stage_idx":   float64(3),
		"stage_codes": map[string]interface{}{"0": "GGrr", "3": "rrGG"},
	})
	if err != nil || !ok {
		t.Fatalf("ApplyAction hold falhou: ok=%v err=%v", ok, err)
	}
	if d.CurrentStage != 4 {
		t.Errorf("Esperado CurrentStage=4 após hold no stage_idx=3, obteve %d", d.CurrentStage)
	}

	// Intergreen (stage 1 is not in [0, 3]) must not return an error
	okInterHold, errInterHold := d.ApplyLogicalAction(1, 1, []int{0, 3}, nil)
	if errInterHold != nil || !okInterHold {
		t.Errorf("ApplyLogicalAction em intergreen (HOLD) falhou: ok=%v err=%v", okInterHold, errInterHold)
	}
	okInterNext, errInterNext := d.ApplyLogicalAction(0, 1, []int{0, 3}, nil)
	if errInterNext != nil || !okInterNext {
		t.Errorf("ApplyLogicalAction em intergreen (NEXT_STAGE) falhou: ok=%v err=%v", okInterNext, errInterNext)
	}

	// Non-blocking ACTIVATE_LOCAL_FIXED_TIME must return immediately (< 500ms)
	start := time.Now()
	okFs, errFs := d.ApplyAction(map[string]interface{}{"action_type": "ACTIVATE_LOCAL_FIXED_TIME"})
	if errFs != nil || !okFs {
		t.Fatalf("ACTIVATE_LOCAL_FIXED_TIME falhou: ok=%v err=%v", okFs, errFs)
	}
	if elapsed := time.Since(start); elapsed > 500*time.Millisecond {
		t.Errorf("ACTIVATE_LOCAL_FIXED_TIME bloqueou por %v (>500ms)", elapsed)
	}

	// Custom all_red_clear_ms must schedule Omit=0 clear asynchronously
	okCustom, errCustom := d.ApplyAction(map[string]interface{}{
		"action_type":      "ACTIVATE_LOCAL_FIXED_TIME",
		"all_red_clear_ms": float64(60),
	})
	if errCustom != nil || !okCustom {
		t.Fatalf("ACTIVATE_LOCAL_FIXED_TIME custom falhou: ok=%v err=%v", okCustom, errCustom)
	}
	time.Sleep(150 * time.Millisecond)
	cleared := false
	for _, s := range agent.Sets() {
		if s.OID == d.Config.PhaseControl.Omit && s.Value == 0 {
			cleared = true
		}
	}
	if !cleared {
		t.Errorf("Esperado Omit=0 após all_red_clear_ms=60ms")
	}
}

func TestNtcipProbeHeartbeatCallbackAndIdempotentRelease(t *testing.T) {
	agent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		"1.3.6.1.2.1.1.1.0":                {Type: gosnmp.OctetString, Value: []byte("Econolite ASC/3 NTCIP Controller")},
		"1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1": {Type: gosnmp.OctetString, Value: []byte{0x03}},
	})

	d := NewDriver("127.0.0.1", agent.Port, "tl_probe", "public", []int{0, 1})
	if err := d.Probe(); err != nil {
		t.Fatalf("Probe esperava sucesso em agente ativo, obteve: %v", err)
	}
	if d.GetBrand() != "Econolite" || d.GetModel() == "" {
		t.Errorf("Metadata inesperada após Probe: brand=%q model=%q", d.GetBrand(), d.GetModel())
	}

	hbStopped := false
	d.SetStopHeartbeatCallback(func() { hbStopped = true })

	ok, err := d.ApplyAction(map[string]interface{}{
		"action_type":      "ACTIVATE_LOCAL_FIXED_TIME",
		"all_red_clear_ms": float64(500),
	})
	if err != nil || !ok {
		t.Fatalf("ACTIVATE_LOCAL_FIXED_TIME falhou: ok=%v err=%v", ok, err)
	}
	if !hbStopped {
		t.Errorf("Esperado StopHeartbeatCb chamado em ACTIVATE_LOCAL_FIXED_TIME")
	}

	// Idempotent ReleaseControl -> Shutdown should send Release SETs once, and cancel pending timer
	_, _ = d.ReleaseControl()
	countBeforeShutdown := len(agent.Sets())
	d.Shutdown()
	countAfterShutdown := len(agent.Sets())
	if countAfterShutdown != countBeforeShutdown {
		t.Errorf("Esperado zero SETs duplicados no Shutdown após ReleaseControl (antes=%d depois=%d)", countBeforeShutdown, countAfterShutdown)
	}

	// Probe on unreachable closed UDP port must fail
	dead := NewDriver("127.0.0.1", 1, "tl_dead", "public", []int{0, 1})
	defer dead.CloseTransport()
	if err := dead.Probe(); err == nil {
		t.Errorf("Esperado erro de Probe em porta inacessível")
	}
}
