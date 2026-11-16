# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit & architectural contract tests for the SOLID + Clean Architecture decomposition
of HardwareGatewayCoordinator and StepProcessor.
"""

import ast
import configparser
import os
import queue
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.central_controller import CentralController
from src.controller.fenix_stage_dispatcher import FenixStageDispatcher
from src.controller.gateway_runtime_worker import GatewayRuntimeWorker
from src.controller.hardware_command_service import HardwareCommandService
from src.controller.hardware_gateway_coordinator import HardwareGatewayCoordinator
from src.drivers.tailscale_gateway_adapter import TailscaleGatewayAdapter
from src.engine.action_supervisor import ActionSupervisor
from src.engine.hardware_telemetry_synchronizer import HardwareTelemetrySynchronizer
from src.engine.step_processor import StepProcessor
from src.engine.strategic_coordinator import StrategicCoordinator
from src.interfaces import (
    IActionSupervisor,
    IAdminGatewayCommands,
    IAIHardwareCommandDispatcher,
    IFailsafeHardwareHook,
    IFenixReconciliationDispatcher,
    IHardwareGatewayCoordinator,
    IHardwareSnapshotProvider,
    IHardwareTelemetrySynchronizer,
    IStrategicCoordinator,
    ITailscaleGatewayAdapter,
)


def _collected_imports(filepath: str) -> set[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
            imports.add(node.module)
    return imports


def test_segregated_protocols_runtime_conformance_isp():
    """Verifies decomposed services & facades conform structurally to narrow Protocol ports."""
    coord = HardwareGatewayCoordinator(sds_data_queue=queue.Queue())
    assert isinstance(coord, IHardwareSnapshotProvider)
    assert isinstance(coord, IFailsafeHardwareHook)
    assert isinstance(coord, IAIHardwareCommandDispatcher)
    assert isinstance(coord, IFenixReconciliationDispatcher)
    assert isinstance(coord, IAdminGatewayCommands)
    assert isinstance(coord, IHardwareGatewayCoordinator)

    adapter = TailscaleGatewayAdapter()
    assert isinstance(adapter, ITailscaleGatewayAdapter)

    syncer = HardwareTelemetrySynchronizer(action_supervisor=MagicMock())
    assert isinstance(syncer, IHardwareTelemetrySynchronizer)

    strat = StrategicCoordinator()
    assert isinstance(strat, IStrategicCoordinator)

    lm = MagicMock()
    lm.get_string.return_value = "ok"
    sup = ActionSupervisor(
        connection_manager=MagicMock(),
        settings=configparser.ConfigParser(),
        state_extractor=MagicMock(),
        locale_manager=lm,
    )
    assert isinstance(sup, IActionSupervisor)


def test_clean_architecture_facade_import_hygiene():
    """Verifies StepProcessor and HardwareGatewayCoordinator stay decoupled from infra/ML internals."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    step_proc_path = os.path.join(project_root, "src", "engine", "step_processor.py")
    coord_path = os.path.join(project_root, "src", "controller", "hardware_gateway_coordinator.py")

    step_imports = _collected_imports(step_proc_path)
    assert "torch" not in step_imports
    assert "numpy" not in step_imports
    assert "evp" not in step_imports

    coord_imports = _collected_imports(coord_path)
    assert "subprocess" not in coord_imports


def test_tailscale_gateway_adapter_commands():
    """Verifies TailscaleGatewayAdapter handles test/enable/disable/unknown cleanly."""
    mock_go = MagicMock()
    mock_go.is_running.return_value = True
    mock_go.send_command.return_value = {
        "success": True,
        "data": {"domain": "node.tail.ts.net", "funnel_active": True},
    }
    subproc_calls = []

    def _fake_run(cmd, **kwargs):
        subproc_calls.append(cmd)
        return SimpleNamespace(returncode=0)

    adapter = TailscaleGatewayAdapter(
        go_client_provider=lambda: mock_go,
        subprocess_runner=_fake_run,
    )

    test_res = adapter.execute("tailscale_test")
    assert test_res["success"] is True
    assert test_res["domain"] == "node.tail.ts.net"

    enable_res = adapter.execute("tailscale_enable", {"port": 2300})
    assert enable_res["success"] is True
    assert subproc_calls == [["tailscale", "funnel", "--bg", "2300"]]
    mock_go.send_command.assert_any_call("tailscale_enable", timeout=10.0, port=2300)

    disable_res = adapter.execute("tailscale_disable")
    assert disable_res["success"] is True
    mock_go.send_command.assert_any_call("tailscale_disable", timeout=5.0)

    unknown_res = adapter.execute("tailscale_bogus")
    assert unknown_res["success"] is False


def test_gateway_runtime_worker_snapshots_events_and_lifecycle():
    """Verifies GatewayRuntimeWorker polling, SDS event classification, and async command execution."""
    driver = MagicMock()
    driver.is_connected = True
    driver.get_status.return_value = {"status": "online", "active_greens": 1}
    conn_mgr = MagicMock()
    conn_mgr.active_connections = {"J1": driver}
    conn_mgr.export_hardware_status_snapshot.return_value = {"J1": {"is_connected": True, "protocol": "NTCIP 1202"}}
    evp_svc = SimpleNamespace(export_remote_snapshot=lambda: {"vehicles": {"V1": {}}, "active_preemptions": {}})
    sds_q: queue.Queue = queue.Queue()

    worker = GatewayRuntimeWorker(
        sds_data_queue=sds_q,
        conn_mgr_provider=lambda _force: conn_mgr,
        evp_service_provider=lambda _force: evp_svc,
        poll_interval_seconds=0.05,
    )

    # Events push cleanly to SDS
    worker.on_go_event({"event": "evp_vehicle", "data": {"id": "AMB-1"}})
    worker.on_go_event({"event": "trap", "ip": "10.0.0.1"})
    assert sds_q.get_nowait() == ("evp_telemetry", {"id": "AMB-1"})
    assert sds_q.get_nowait() == ("hardware_trap", {"event": "trap", "ip": "10.0.0.1"})

    # Async start + stop + task queue
    worker.start()
    try:
        ran = []
        done = queue.Queue()
        worker.submit_task(lambda v: (ran.append(v), done.put(True)), 42)
        assert done.get(timeout=1.5) is True
        assert ran == [42]

        tls_copy, hw_copy, evp_copy = worker.get_cached_frame_attachments()
        assert tls_copy["J1"]["active_greens"] == 1
        assert hw_copy["J1"]["is_connected"] is True
        assert "V1" in evp_copy["vehicles"]
    finally:
        worker.stop()


def test_hardware_command_service_dispatch_and_override_release():
    """Verifies HardwareCommandService command dispatch maps, injected config repo, and override release."""
    driver = MagicMock()
    driver.is_connected = True
    driver.intersection_id = "J1"
    driver.hardware_driver = MagicMock()
    driver.hardware_driver.release_control.return_value = True
    driver.apply_action.return_value = True
    driver.apply_logical_action.return_value = True
    driver.apply_decision.return_value = True

    conn_mgr = MagicMock()
    conn_mgr.active_connections = {"J1": driver}
    conn_mgr.saved_ips = {}
    conn_mgr.saved_snmp_configs = {}
    conn_mgr.toggle_connection.return_value = True

    config_repo = MagicMock()
    go_client = MagicMock()
    go_client.is_running.return_value = True
    go_client.send_command.return_value = {"success": True}
    sds_events = []

    svc = HardwareCommandService(
        conn_mgr_provider=lambda _force: conn_mgr,
        go_client_provider=lambda _force: go_client,
        evp_service_provider=lambda _force: None,
        refresh_snapshots=lambda _push: ({}, {"J1": {"is_connected": True}}, None),
        push_sds_event=lambda evt: sds_events.append(evt),
        config_repo=config_repo,
    )

    ok_cnt, fail_cnt = svc.sync_hardware_csv(
        {"entries": {"J1": {"ip": "10.0.0.8", "snmp_config": {"version": "v2c"}}}, "save_to_db": True}
    )
    assert (ok_cnt, fail_cnt) == (1, 0)
    config_repo.save_connection_db.assert_called_once()

    assert (
        svc.execute_ai_hardware_cmd(
            {"intersection_id": "J1", "cmd": "apply_action", "action_data": {"action_type": "hold"}}
        )
        is True
    )
    assert (
        svc.execute_ai_hardware_cmd(
            {
                "intersection_id": "J1",
                "cmd": "apply_logical_action",
                "action": 1,
                "current_stage_idx": 0,
                "green_stages": [0, 2],
            }
        )
        is True
    )
    assert svc.execute_ai_hardware_cmd({"intersection_id": "J1", "cmd": "apply_decision", "action": "HOLD"}) is True
    assert svc.execute_ai_hardware_cmd({"intersection_id": "J1", "cmd": "release_control"}) is True
    assert svc.execute_ai_hardware_cmd({"intersection_id": "J1", "cmd": "nonexistent_cmd"}) is False

    svc.sync_override_to_hardware(["J1"], "ALERT")
    driver.apply_action.assert_any_call({"action_type": "flash"})
    svc.sync_override_to_hardware(["J1"], "AUTOMATIC")
    driver.apply_action.assert_any_call({"action_type": "release_flash"})

    assert svc.execute_ai_evp_preempt({"intersection_id": "J1", "action_data": {"stage": 1}}) is True
    go_client.send_command.assert_called_with("evp_preempt", intersection_id="J1", action_data={"stage": 1})


def test_hardware_telemetry_synchronizer_calls_record_stage_change():
    """Verifies HardwareTelemetrySynchronizer uses ActionSupervisor.record_stage_change and evp_snapshot_sink."""
    lm = MagicMock()
    lm.get_string.return_value = "ok"
    conn_mgr = MagicMock()
    conn_mgr.active_connections = {}
    sup = ActionSupervisor(
        connection_manager=conn_mgr,
        settings=configparser.ConfigParser(),
        state_extractor=MagicMock(),
        locale_manager=lm,
    )
    extractor = SimpleNamespace(
        tl_green_stages={"J1": [0, 2]},
        tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}},
    )
    reconciler = MagicMock()
    evp_snapshots = []

    syncer = HardwareTelemetrySynchronizer(
        action_supervisor=sup,
        state_extractor=extractor,
        state_reconciler=reconciler,
        evp_snapshot_sink=lambda snap: evp_snapshots.append(snap),
    )

    stages = {"J1": 0}
    syncer.sync(
        traffic_data={
            "evp_state": {"vehicles": {"V1": {}}, "active_preemptions": {}},
            "tls_telemetry": {"J1": {"status": "online", "protocol": "NTCIP 1202", "active_greens": 12}},
        },
        agents={"J1": MagicMock()},
        sim_time=42.5,
        current_stages=stages,
    )

    assert evp_snapshots == [{"vehicles": {"V1": {}}, "active_preemptions": {}}]
    assert stages["J1"] == 2
    assert sup._last_stage_change_time["J1"] == 42.5
    reconciler.on_stage_transition_detected.assert_called_with("J1", 2)


def test_central_controller_container_wires_hardware_gateway_coordinator_override():
    """Verifies CentralControllerContainer accepts and injects hardware_gateway_coordinator override (DIP)."""
    config = configparser.ConfigParser()
    config.add_section("WATCHDOG")
    config.set("WATCHDOG", "heartbeat_timeout_seconds", "5.0")

    mock_gw_coord = MagicMock(spec=HardwareGatewayCoordinator)
    injected = {
        "override_manager": MagicMock(),
        "telemetry_aggregator": MagicMock(),
        "health_monitor": MagicMock(),
        "monitor_client": MagicMock(),
        "topology_manager": MagicMock(),
        "db_manager": None,
        "traffic_data_recorder": None,
        "yellow_schedule_manager": MagicMock(),
        "readiness_latch": MagicMock(),
        "topology_recorder_bridge": MagicMock(),
        "hft_system_facade": MagicMock(),
        "grpc_server_manager": MagicMock(),
        "hft_event_loop": MagicMock(),
        "hardware_gateway_coordinator": mock_gw_coord,
    }

    cc = CentralController(
        settings=config,
        ai_pipe_conn=MagicMock(),
        watchdog_queue=MagicMock(),
        sds_data_queue=MagicMock(),
        sas_data_queue=MagicMock(),
        ui_command_queue=MagicMock(),
        locale_manager=MagicMock(),
        services=injected,
    )

    assert cc.hardware_gateway_coordinator is mock_gw_coord
    assert cc.failsafe_manager.hardware_gateway_coordinator is mock_gw_coord
    assert cc.traffic_frame_processor.hardware_gateway_coordinator is mock_gw_coord
    assert cc.request_processor.hardware_gateway_coordinator is mock_gw_coord
    assert cc.request_processor.ai_handler.hardware_gateway_coordinator is mock_gw_coord


def test_fenix_stage_dispatcher_and_step_processor_property_forwarding():
    """Verifies FenixStageDispatcher resolution/handover and StepProcessor collaborator property sync."""
    fenix_q: queue.Queue = queue.Queue()
    pipe = MagicMock()
    pipe.closed = False
    topo = SimpleNamespace(tls_phases_cache={"J1": 0, "J2": 3})

    dispatcher = FenixStageDispatcher(
        conn_mgr_provider=lambda _force: None,
        refresh_snapshots=lambda _push: (
            {"J1": {"status": "online", "protocol": "NTCIP 1202", "active_greens": 12}},
            {},
            None,
        ),
        topology_manager=topo,
        ai_pipe_provider=lambda: pipe,
        fenix_queue_provider=lambda: fenix_q,
        green_stages_lookup=lambda _tl: [0, 2],
        stage_codes_lookup=lambda _tl, _lm: {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"},
    )

    stages = dispatcher.dispatch_fenix_reconcile_stages()
    assert stages == {"J1": 2, "J2": 3}
    pipe.send.assert_called_once_with(("fenix", "reconcile_stages", ({"J1": 2, "J2": 3},), {}))

    assert dispatcher.handle_fenix_handover_complete({"source": "unit_test"}) is True
    assert fenix_q.get_nowait() == ("HANDOVER_COMPLETE", {"source": "unit_test"})

    settings = configparser.ConfigParser()
    proc = StepProcessor(
        settings=settings,
        locale_manager=MagicMock(),
        step_timer=MagicMock(),
        agent_evaluator=MagicMock(),
        stage_transition_manager=MagicMock(),
        action_supervisor=MagicMock(),
        online_pae_trainer=MagicMock(),
        mfd_processor=MagicMock(),
        hardware_actuator=MagicMock(),
        telemetry_publisher=MagicMock(),
        cycle_manager=MagicMock(),
        episode_reporter=MagicMock(),
    )
    new_reconciler = MagicMock()
    new_extractor = SimpleNamespace(tl_green_stages={"J1": [0]}, tl_stage_codes={"J1": {0: "GGrr"}})
    proc.state_reconciler = new_reconciler
    proc.state_extractor = new_extractor
    assert proc.hardware_synchronizer.state_reconciler is new_reconciler
    assert proc.hardware_synchronizer.state_extractor is new_extractor
    assert proc.strategic_coordinator.state_extractor is new_extractor
