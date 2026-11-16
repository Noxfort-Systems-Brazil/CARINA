// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package utmc

import (
	"testing"
	"time"

	"carina/src_go/pkg/snmptest"
	"github.com/gosnmp/gosnmp"
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

	// Sparse greenStages ([0, 3]): stage_idx 3 is ordinal 1 -> mask 2 (1<<1)
	maskSparse := d.ConvertStageToHardwareMask(3, []int{0, 3}, nil)
	if maskSparse != 2 {
		t.Errorf("Esperado 2 (1<<1) para stage_idx esparso 3 em [0, 3], obteve %d", maskSparse)
	}
}

func TestUtmcMockUdpActionsAndTelemetry(t *testing.T) {
	agent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		"1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1": {Type: gosnmp.OctetString, Value: []byte{0x02}},
		"1.3.6.1.4.1.2825.4.2.1.1.4.1.6.1": {Type: gosnmp.Integer, Value: 1},
		"1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1": {Type: gosnmp.Integer, Value: 2},
		"1.3.6.1.4.1.2825.4.2.1.1.4.1.7.1": {Type: gosnmp.Integer, Value: 0},
	})

	d := NewDriver("127.0.0.1", agent.Port, "tl_utmc_test", "public", []int{0, 3})
	defer d.Shutdown()

	tel, err := d.GetTelemetry()
	if err != nil {
		t.Fatalf("GetTelemetry falhou: %v", err)
	}
	if tel["status"] != "online" {
		t.Errorf("Esperado status online, obteve %v", tel["status"])
	}
	if tel["active_greens"] != int64(2) {
		t.Errorf("Esperado active_greens=2, obteve %v", tel["active_greens"])
	}
	if tel["active_veh_calls"] != int64(2) {
		t.Errorf("Esperado active_veh_calls=2, obteve %v", tel["active_veh_calls"])
	}

	ok, err := d.ApplyAction(map[string]interface{}{
		"action_type": "hold",
		"stage_idx":   float64(3),
	})
	if err != nil || !ok {
		t.Fatalf("ApplyAction hold falhou: ok=%v err=%v", ok, err)
	}
	if d.CurrentStage != 2 {
		t.Errorf("Esperado CurrentStage ordinal 2 após hold em stage_idx=3 de [0,3], obteve %d", d.CurrentStage)
	}

	// Check SET used sparse mask 2 on UTMC stage hold OID
	var holdMask interface{}
	for _, s := range agent.Sets() {
		if s.OID == d.Config.StageControl.Hold {
			holdMask = s.Value
		}
	}
	if holdMask != 2 {
		t.Errorf("Esperado Hold SET=2, obteve %v", holdMask)
	}

	// Intergreen (stage 1 is not in [0, 3])
	if okInter, errInter := d.ApplyLogicalAction(1, 1, []int{0, 3}, nil); errInter != nil || !okInter {
		t.Errorf("ApplyLogicalAction intergreen HOLD falhou: ok=%v err=%v", okInter, errInter)
	}
	if okNext, errNext := d.ApplyLogicalAction(0, 1, []int{0, 3}, nil); errNext != nil || !okNext {
		t.Errorf("ApplyLogicalAction intergreen NEXT_STAGE falhou: ok=%v err=%v", okNext, errNext)
	}

	// Non-blocking ACTIVATE_LOCAL_FIXED_TIME
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
		if s.OID == d.Config.StageControl.Omit && s.Value == 0 {
			cleared = true
		}
	}
	if !cleared {
		t.Errorf("Esperado Omit=0 após all_red_clear_ms=60ms")
	}
}

func TestUtmcProbeHeartbeatCallbackAndIdempotentRelease(t *testing.T) {
	agent := snmptest.StartMockAgent(t, map[string]gosnmp.SnmpPDU{
		"1.3.6.1.2.1.1.1.0":                {Type: gosnmp.OctetString, Value: []byte("Siemens ST950 UTMC Controller")},
		"1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1": {Type: gosnmp.OctetString, Value: []byte{0x01}},
	})

	d := NewDriver("127.0.0.1", agent.Port, "tl_utmc_probe", "public", []int{0, 1})
	if err := d.Probe(); err != nil {
		t.Fatalf("Probe esperava sucesso em agente UTMC ativo, obteve: %v", err)
	}
	if d.GetBrand() != "Siemens" || d.GetModel() != "ST950" {
		t.Errorf("Metadata inesperada após Probe UTMC: brand=%q model=%q", d.GetBrand(), d.GetModel())
	}

	hbStopped := false
	d.SetStopHeartbeatCallback(func() { hbStopped = true })

	ok, err := d.ApplyAction(map[string]interface{}{
		"action_type":      "ACTIVATE_LOCAL_FIXED_TIME",
		"all_red_clear_ms": float64(500),
	})
	if err != nil || !ok {
		t.Fatalf("ACTIVATE_LOCAL_FIXED_TIME UTMC falhou: ok=%v err=%v", ok, err)
	}
	if !hbStopped {
		t.Errorf("Esperado StopHeartbeatCb chamado em ACTIVATE_LOCAL_FIXED_TIME UTMC")
	}

	_, _ = d.ReleaseControl()
	countBeforeShutdown := len(agent.Sets())
	d.Shutdown()
	countAfterShutdown := len(agent.Sets())
	if countAfterShutdown != countBeforeShutdown {
		t.Errorf("Esperado zero SETs duplicados no Shutdown após ReleaseControl (antes=%d depois=%d)", countBeforeShutdown, countAfterShutdown)
	}

	dead := NewDriver("127.0.0.1", 1, "tl_utmc_dead", "public", []int{0, 1})
	defer dead.CloseTransport()
	if err := dead.Probe(); err == nil {
		t.Errorf("Esperado erro de Probe UTMC em porta inacessível")
	}
}
