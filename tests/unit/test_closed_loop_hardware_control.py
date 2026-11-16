# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.controller.connection_config_repo import ConnectionConfigRepository
from src.drivers.driver_factory import DriverFactory
from src.drivers.hardware_stage_actuator import HardwareStageActuator
from src.drivers.hardware_telemetry_decoder import decode_stage_from_telemetry, resolve_tl_key
from src.engine.action_supervisor import ActionSupervisor
from src.engine.step_processor import StepProcessor
from src.engine.step_telemetry_publisher import StepTelemetryPublisher
from src.engine.step_timer import StepTimer
from src.evp.evp_bridge import EVPBridge


class _FakeLocale:
    def get_string(self, key, default="", **kwargs):
        if default:
            try:
                return default.format(**kwargs)
            except Exception:
                return default
        return key


@pytest.fixture(autouse=True)
def _reset_evp_bridge_hooks():
    prev_disp = EVPBridge._remote_dispatcher
    prev_prov = EVPBridge._stage_metadata_provider
    yield
    EVPBridge.configure_remote_dispatcher(prev_disp)
    EVPBridge.configure_stage_metadata_provider(prev_prov)


# =========================================================================
# PHASE 1: HARDWARE TELEMETRY DECODER, ACTION SUPERVISOR, STEP PROCESSOR
# =========================================================================


def test_decode_stage_ntcip_and_utmc_bitmasks_and_intergreens():
    stage_codes = {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}
    green_stages = [0, 2]

    # UTMC ordinal bitmask: bit 1 -> green_stages[1] == 2
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "protocol": "UTMC2", "active_greens": 0b10},
            green_stages=green_stages,
            stage_codes=stage_codes,
        )
        == 2
    )

    # NTCIP green bitmask matching stage 2 ('rrGG' -> bits 2 and 3 = 0b1100 = 12)
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "protocol": "NTCIP 1202", "active_greens": 12},
            green_stages=green_stages,
            stage_codes=stage_codes,
        )
        == 2
    )

    # Yellow intergreen detection (no greens, active_yellows matching stage 1 'yyrr' -> 0b0011 = 3)
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "protocol": "NTCIP 1202", "active_greens": 0, "active_yellows": 3},
            green_stages=green_stages,
            stage_codes=stage_codes,
            current_stage_hint=0,
        )
        == 1
    )

    # All-red clearance detection
    all_red_codes = {0: "GGrr", 1: "yyrr", 2: "rrrr", 3: "rrGG"}
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "protocol": "NTCIP 1202", "active_greens": 0, "active_yellows": 0, "active_reds": 15},
            green_stages=[0, 3],
            stage_codes=all_red_codes,
            current_stage_hint=1,
        )
        == 2
    )

    # Offline telemetry returns None and safe_telemetry_int rejects booleans
    assert (
        decode_stage_from_telemetry(
            {"status": "offline", "active_greens": True},
            green_stages=green_stages,
            stage_codes=stage_codes,
        )
        is None
    )
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "active_greens": True, "current_stage": 2},
            green_stages=[0, 2],
            stage_codes=stage_codes,
        )
        == 1
    )
    assert (
        decode_stage_from_telemetry(
            {"status": "online", "protocol": "NTCIP 1202", "current_stage": 1},
            green_stages=[],
            stage_codes={},
        )
        == 0
    )


def test_resolve_tl_key_normalizes_prefix():
    mapping = {"tl_J1": {"status": "online"}, "J2": {"status": "online"}}
    assert resolve_tl_key("J1", mapping) == "tl_J1"
    assert resolve_tl_key("tl_J2", mapping) == "J2"
    assert resolve_tl_key("missing", mapping) is None


def test_action_supervisor_dispatches_advance_and_hold_respecting_vetoes_and_overrides():
    driver = MagicMock()
    driver.is_connected = True
    conn_mgr = SimpleNamespace(active_connections={"J1": driver})
    extractor = SimpleNamespace(
        tl_green_stages={"J1": [0, 2]},
        tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}},
    )
    settings = configparser.ConfigParser()
    supervisor = ActionSupervisor(conn_mgr, settings, extractor, _FakeLocale())

    # Veto blocks NEXT_STAGE (0) for J1, forcing HOLD
    supervisor.update_vetos({"J1": {"veto_action": 0}})
    actions = {"J1": 0}
    supervisor.apply_actions(actions, current_sim_time=1.0, current_stages={"J1": 0})
    assert actions["J1"] == 1
    driver.apply_logical_action.assert_not_called()

    # Without veto, NEXT_STAGE (0) forwards apply_logical_action with stage metadata
    supervisor.apply_actions({"J1": 0}, current_sim_time=2.0, current_stages={"J1": 0})
    driver.apply_logical_action.assert_called_once_with(0, 0, [0, 2], {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"})

    # send_stage_hold dispatches 1-based stage + 0-based stage_idx + stage_codes
    supervisor.send_stage_hold("J1", 2)
    driver.apply_action.assert_called_once_with(
        {
            "action_type": "hold",
            "stage": 3,
            "stage_idx": 2,
            "stage_codes": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"},
        }
    )

    # Active ALERT override blocks holds and advances
    driver.reset_mock()
    supervisor.override_states["J1"] = "ALERT"
    supervisor.apply_actions({"J1": 0}, current_sim_time=3.0, current_stages={"J1": 0})
    supervisor.send_stage_hold("J1", 0)
    driver.apply_logical_action.assert_not_called()
    driver.apply_action.assert_not_called()


def test_hardware_stage_actuator_holds_green_stages_and_skips_intergreens():
    driver = MagicMock()
    driver.is_connected = True
    conn_mgr = SimpleNamespace(active_connections={"J1": driver})
    extractor = SimpleNamespace(
        tl_green_stages={"J1": [0, 2]},
        tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}},
    )
    supervisor = MagicMock()
    supervisor.connection_manager = conn_mgr
    supervisor._get_stage_metadata.return_value = ([0, 2], extractor.tl_stage_codes["J1"])

    actuator = HardwareStageActuator()

    # Transition to yellow intergreen stage (1): should NOT hold hardware
    actuator.sync_hardware_stages(supervisor, {"J1": 1}, extractor)
    supervisor.send_stage_hold.assert_not_called()
    driver.log_carina_colors.assert_called_with(1, extractor.tl_stage_codes["J1"])

    # Transition to green stage (2): MUST send hold
    actuator.sync_hardware_stages(supervisor, {"J1": 2}, extractor)
    supervisor.send_stage_hold.assert_called_once_with("J1", 2)


def test_step_processor_closed_loop_telemetry_decoding_and_pipe_publish():
    driver = MagicMock()
    driver.is_connected = True
    driver.get_status.return_value = {"status": "online", "active_greens": 12}

    conn_mgr = MagicMock()
    conn_mgr.active_connections = {"J1": driver}

    extractor = SimpleNamespace(
        tl_green_stages={"J1": [0, 2]},
        tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}},
    )
    action_supervisor = MagicMock()
    action_supervisor.connection_manager = conn_mgr
    action_supervisor._last_stage_change_time = {}

    agent_evaluator = MagicMock()
    agent_evaluator.evaluate_fleet.return_value = SimpleNamespace(
        actions={"J1": 1},
        lanes_state={},
        maturity_info={},
        step_reward_sum=0.0,
        metrics_delta={},
        guardian_vetoed_any=False,
    )

    state_reconciler = MagicMock()
    pipe_conn = MagicMock()
    telemetry_publisher = StepTelemetryPublisher(pipe_conn=pipe_conn)

    settings = configparser.ConfigParser()
    processor = StepProcessor(
        settings=settings,
        locale_manager=_FakeLocale(),
        step_timer=StepTimer(),
        agent_evaluator=agent_evaluator,
        stage_transition_manager=MagicMock(),
        action_supervisor=action_supervisor,
        online_pae_trainer=MagicMock(),
        mfd_processor=MagicMock(process_step=MagicMock(return_value={})),
        hardware_actuator=MagicMock(),
        telemetry_publisher=telemetry_publisher,
        cycle_manager=MagicMock(),
        episode_reporter=MagicMock(),
        state_reconciler=state_reconciler,
        state_extractor=extractor,
    )
    processor.set_current_phases({"J1": 0})
    processor.log_step_progress = False

    # Case 1: Upstream injected tls_telemetry -> driver.get_status is NOT polled again, stage updates from 0 -> 2
    traffic_data = {
        "timestamp": 100.0,
        "sequence_id": 1,
        "edges": {},
        "tls_telemetry": {"J1": {"status": "online", "protocol": "NTCIP 1202", "active_greens": 12}},
        "hardware_status": {"J1": {"is_connected": True, "brand": "Tesc", "model": "TC-1"}},
    }
    processor.process_hft_step(traffic_data, {"J1": MagicMock()})

    driver.get_status.assert_not_called()
    assert processor.current_stages["J1"] == 2
    state_reconciler.on_stage_transition_detected.assert_called_with("J1", 2)
    conn_mgr.update_remote_hardware_status.assert_called_once()
    sent_tuple = pipe_conn.send.call_args[0][0]
    assert sent_tuple[0] == "ai_telemetry_sync"
    assert sent_tuple[1]["hardware_status"]["J1"]["brand"] == "Tesc"

    # Case 2: No upstream tls_telemetry -> falls back to polling driver.get_status()
    driver.get_status.return_value = {"status": "online", "protocol": "NTCIP 1202", "active_greens": 3}
    traffic_data_fallback = {"timestamp": 101.0, "sequence_id": 2, "edges": {}}
    extractor.tl_stage_codes["J1"] = {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}
    processor.process_hft_step(traffic_data_fallback, {"J1": MagicMock()})
    driver.get_status.assert_called_once()


# =========================================================================
# PHASE 4: EVP BRIDGE STAGE MAPPING & REMOTE IPC DISPATCH
# =========================================================================


def test_evp_bridge_stage_mapping_and_remote_dispatcher(monkeypatch):
    EVPBridge.configure_stage_metadata_provider(
        lambda tl_id: ([0, 2, 4], {0: "GGrrrr", 1: "yyrrrr", 2: "rrGGrr", 4: "rrrrGG"})
    )
    stage_idx, stage_codes = EVPBridge.resolve_stage_mapping("tl_A", 2)
    assert stage_idx == 2
    assert stage_codes[2] == "rrGGrr"

    # Out-of-bounds target falls back cleanly to max(0, target_stage - 1)
    fallback_idx, _ = EVPBridge.resolve_stage_mapping("tl_A", 0, green_stages=[1, 3], stage_codes={})
    assert fallback_idx == 1

    dispatched = []
    EVPBridge.configure_remote_dispatcher(lambda tl_id, cmd: dispatched.append((tl_id, cmd)))
    monkeypatch.setenv("CARINA_GATEWAY_ROLE", "remote")

    mock_evp_service = MagicMock()
    bridge = EVPBridge(evp_service=mock_evp_service)
    mock_evp_service.on_action_dispatch("tl_A", 3, "ACTIVATE_PREEMPT")

    assert len(dispatched) == 1
    assert dispatched[0][0] == "tl_A"
    assert dispatched[0][1]["action_type"] == "activate_preempt"
    assert dispatched[0][1]["stage_idx"] == 4


# =========================================================================
# PHASE 5: OPTIONAL SNMPv2c/v3 CONFIG PLUMBING
# =========================================================================


def test_snmp_config_csv_db_and_driver_factory_plumbing(tmp_path):
    csv_file = tmp_path / "hardware_snmp3.csv"
    csv_file.write_text(
        "intersection_id,ip_address,snmp_version,security_level,username,auth_protocol,auth_passphrase,priv_protocol,priv_passphrase\n"
        "J1,10.0.0.10,3,authPriv,carina_ops,SHA256,secretAuth,AES128,secretPriv\n"
        "J2,10.0.0.11,2c,,,,,,,\n",
        encoding="utf-8",
    )

    entries = ConnectionConfigRepository.import_csv_entries(str(csv_file))
    assert entries["J1"]["ip"] == "10.0.0.10"
    assert entries["J1"]["snmp_config"]["snmp_version"] == "3"
    assert entries["J1"]["snmp_config"]["username"] == "carina_ops"
    assert entries["J1"]["snmp_config"]["priv_protocol"] == "AES128"
    assert entries["J2"]["snmp_config"] == {"snmp_version": "2c"}

    # Database roundtrip on isolated temp SQLite file
    import sqlite3

    db_path = tmp_path / "test_conn.sqlite3"

    class _FakeEngine:
        db_type = "sqlite"

        def get_connection(self):
            return sqlite3.connect(str(db_path))

    fake_engine = _FakeEngine()
    conn = fake_engine.get_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS hardware_controller_connections ("
        "intersection_id TEXT PRIMARY KEY, ip_address TEXT NOT NULL, auto_connect INTEGER DEFAULT 1, "
        "last_connected TEXT DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()

    assert ConnectionConfigRepository.save_connection_db(
        "J1", "10.0.0.10", snmp_config=entries["J1"]["snmp_config"], engine=fake_engine
    )
    loaded = ConnectionConfigRepository.load_connection_configs_with_snmp_db(engine=fake_engine)
    assert loaded["J1"]["ip"] == "10.0.0.10"
    assert loaded["J1"]["snmp_config"]["auth_protocol"] == "SHA256"

    snmp_only = ConnectionConfigRepository.load_all_snmp_configs_db(engine=fake_engine)
    assert snmp_only["J1"]["username"] == "carina_ops"

    # DriverFactory forwards snmp_config to GoGatewayClient.connect_intersection
    mock_go = MagicMock()
    mock_go.is_running.return_value = True
    mock_go.connect_intersection.return_value = {
        "success": True,
        "data": {"protocol": "NTCIP 1202", "brand": "Brascontrol", "model": "BC-X"},
    }
    with patch("src.drivers.driver_factory.GoGatewayClient.get_instance", return_value=mock_go):
        proxy = DriverFactory.create_and_connect_driver(
            "10.0.0.10", 161, "public", "J1", snmp_config=entries["J1"]["snmp_config"]
        )

    assert proxy is not None
    mock_go.connect_intersection.assert_called_once()
    assert mock_go.connect_intersection.call_args.kwargs["snmp_config"]["username"] == "carina_ops"
