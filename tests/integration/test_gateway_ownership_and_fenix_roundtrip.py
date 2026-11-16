# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import queue
from multiprocessing import Pipe
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.controller.connection_manager import HardwareConnectionManager
from src.controller.failsafe_manager import FailsafeManager
from src.controller.hardware_gateway_coordinator import HardwareGatewayCoordinator
from src.controller.request_processor import RequestProcessor
from src.controller.traffic_frame_processor import TrafficFrameProcessor
from src.drivers.go_gateway_client import GoGatewayClient
from src.drivers.remote_hardware_driver import RemoteHardwareDriverProxy
from src.engine.event_router import EventRouter
from src.engine.step_processor import StepProcessor
from src.engine.step_telemetry_publisher import StepTelemetryPublisher
from src.engine.step_timer import StepTimer
from src.fenix.state_reconciler import StateReconciler
from src.handlers.ai_request_handler import AIRequestHandler
from src.launcher.process_manager import ProcessManager
from ui.controllers.remote_gateway_controller import RemoteGatewayController
from ui.handlers.hardware_settings_handler import HardwareSettingsHandler
from ui.handlers.network_event_handler import NetworkEventHandler


class _FakeLocale:
    def get_string(self, key, default="", **kwargs):
        if default:
            try:
                return default.format(**kwargs)
            except Exception:
                return default
        return key


@pytest.fixture(autouse=True)
def _restore_singletons():
    prev_hw = HardwareConnectionManager._active_instance
    prev_go = GoGatewayClient._instance
    yield
    HardwareConnectionManager._active_instance = prev_hw
    GoGatewayClient._instance = prev_go


# =========================================================================
# PHASE 2: SINGLE GATEWAY OWNER, REMOTE PROXY & UI/AI/CONTROLLER ISOLATION
# =========================================================================


def test_remote_role_blocks_local_go_spawn_and_udp_trap_listener(monkeypatch):
    monkeypatch.setenv("CARINA_GATEWAY_ROLE", "remote")

    gw = GoGatewayClient(binary_path="/nonexistent/carina-go")
    assert gw.is_remote_gateway_role() is True
    assert gw.start() is False
    res = gw.send_command("ping")
    assert res["success"] is False

    with (
        patch.object(HardwareConnectionManager, "_discover_intersections", return_value=["tl_J1"]),
        patch(
            "src.controller.connection_config_repo.ConnectionConfigRepository.load_all_connections_db",
            return_value={"tl_J1": "10.0.0.5"},
        ),
    ):
        mgr = HardwareConnectionManager(locale_manager=_FakeLocale())

        assert mgr.event_listener is None
        assert mgr.saved_ips["tl_J1"] == "10.0.0.5"
        assert mgr.is_intersection_connected("tl_J1") is False

        mgr.update_remote_hardware_status(
            {
                "tl_J1": {
                    "is_connected": True,
                    "brand": "Dataprom",
                    "model": "DP-40",
                    "protocol": "NTCIP 1202",
                    "ip_address": "10.0.0.5",
                }
            }
        )
        assert mgr.is_intersection_connected("tl_J1") is True
        assert mgr.get_hardware_info("tl_J1")["brand"] == "Dataprom"
        ui_list = mgr.get_ui_status_list()
        j1_entry = next(item for item in ui_list if item["agent_id"] == "tl_J1")
        assert j1_entry["status"] == "NTCIP 1202"


def test_remote_hardware_driver_proxy_and_coordinator_roundtrip():
    ctrl_conn, ai_conn = Pipe(duplex=True)
    try:
        proxy = RemoteHardwareDriverProxy(
            intersection_id="J1",
            ip_address="192.168.1.50",
            protocol_name="NTCIP 1202",
            brand="Focus",
            model="FX-200",
            green_stages=[0, 2],
            stage_codes={0: "GGrr", 2: "rrGG"},
            pipe_conn=ai_conn,
        )

        assert proxy.apply_logical_action(0, 0, [0, 2], {0: "GGrr", 2: "rrGG"}) is True
        assert proxy.apply_action({"action_type": "hold", "stage": 3, "stage_idx": 2}) is True
        assert proxy.release_control() is True

        # Coordinator in CentralController handles all three 2-tuples locally without writing back on pipe
        owner_driver = MagicMock()
        owner_driver.is_connected = True
        owner_driver.hardware_driver = MagicMock()
        owner_conn_mgr = MagicMock()
        owner_conn_mgr.active_connections = {"J1": owner_driver}

        coordinator = HardwareGatewayCoordinator(
            sds_data_queue=queue.Queue(),
            ai_pipe_conn=ctrl_conn,
            connection_manager=owner_conn_mgr,
            go_client=MagicMock(),
            evp_service=MagicMock(),
        )

        ai_handler = AIRequestHandler(
            locale_manager=_FakeLocale(),
            topology_manager=MagicMock(),
            sds_queue=queue.Queue(),
            sas_queue=queue.Queue(),
            health_monitor=MagicMock(),
            override_manager=MagicMock(is_ai_command_blocked=MagicMock(return_value=False)),
        )
        ai_handler.hardware_gateway_coordinator = coordinator

        for _ in range(3):
            msg = ctrl_conn.recv()
            assert len(msg) == 2 and msg[0] == "ai_hardware_cmd"
            ai_handler.process(msg, sumo_conn=None, ai_pipe_conn=ctrl_conn, override_commands_buffer=[])

        assert not ai_conn.poll(0.05)  # 2-tuple never writes a reply on pipe!
        owner_driver.apply_logical_action.assert_called_once_with(0, 0, [0, 2], stage_codes={0: "GGrr", 2: "rrGG"})
        owner_driver.apply_action.assert_called_once_with({"action_type": "hold", "stage": 3, "stage_idx": 2})
        owner_driver.hardware_driver.release_control.assert_called_once()
    finally:
        ctrl_conn.close()
        ai_conn.close()


def test_event_router_remote_role_materializes_and_prunes_proxies(monkeypatch):
    monkeypatch.setenv("CARINA_GATEWAY_ROLE", "remote")

    conn_mgr = MagicMock()
    conn_mgr.active_connections = {}
    supervisor = MagicMock()
    trainer = SimpleNamespace(connection_manager=conn_mgr, action_supervisor=supervisor, agents={}, is_running=True)
    step_proc = MagicMock()
    pipe = MagicMock()
    router = EventRouter(pipe_conn=pipe, trainer_instance=trainer, agent_manager=MagicMock(), step_processor=step_proc)

    router._execute_command(
        "hardware",
        "toggle_connection",
        ("J1", "10.0.0.10", "connect"),
        kwargs={
            "hardware_status": {
                "J1": {
                    "is_connected": True,
                    "ip_address": "10.0.0.10",
                    "brand": "Kopp",
                    "model": "K-10",
                    "protocol": "UTMC2",
                }
            }
        },
    )
    assert "J1" in conn_mgr.active_connections
    assert isinstance(conn_mgr.active_connections["J1"], RemoteHardwareDriverProxy)
    conn_mgr.toggle_connection.assert_not_called()

    # Empty authoritative hardware_status prunes proxy and cleans up supervisor
    router._execute_command(
        "hardware",
        "toggle_connection",
        ("J1", "10.0.0.10", "disconnect"),
        kwargs={"hardware_status": {}},
    )
    assert "J1" not in conn_mgr.active_connections
    supervisor.cleanup_intersection.assert_called_with("J1")

    # Failsafe state resets hardware_actuator so next hold re-locks cleanly
    router._execute_command("hardware", "failsafe_state", (False,), kwargs={})
    step_proc.hardware_actuator.reset.assert_called_once()


def test_ui_remote_routing_without_local_go_process(monkeypatch, tmp_path):
    monkeypatch.setenv("CARINA_GATEWAY_ROLE", "remote")

    settings_client = MagicMock()
    mock_go = MagicMock()
    rg_ctrl = RemoteGatewayController(go_client=mock_go, settings_client=settings_client)

    results = []
    rg_ctrl.test_connection_async(on_result=lambda ok, msg: results.append((ok, msg)))
    settings_client.send_command.assert_called_with("tailscale_test", {})
    mock_go.send_command.assert_not_called()

    rg_ctrl.connect_gateway_async(on_result=lambda ok, msg: results.append((ok, msg)))
    settings_client.send_command.assert_called_with("tailscale_enable", {"port": 2201})

    rg_ctrl.disconnect_gateway()
    settings_client.send_command.assert_called_with("tailscale_disable", {})

    # Simulate SDS tailscale_response arrival through NetworkEventHandler
    fake_rg_card = MagicMock()
    fake_settings_view = SimpleNamespace(account_card=None, hardware_handler=None, remote_gateway_card=fake_rg_card)
    net_handler = NetworkEventHandler(
        page=MagicMock(),
        dashboard_view=MagicMock(),
        security_ui=MagicMock(),
        settings_view=fake_settings_view,
        locale_manager=_FakeLocale(),
    )
    net_handler.handle_sds_data(
        {
            "type": "tailscale_response",
            "payload": {"action": "tailscale_test", "success": True, "domain": "carina.ts.net", "message": "OK"},
        }
    )
    fake_rg_card.handle_remote_response.assert_called_once()
    rg_ctrl.handle_remote_response(
        {"action": "tailscale_test", "success": True, "domain": "carina.ts.net", "message": "OK"}
    )
    assert results == [(True, "OK")]

    # CSV import in UI remote role parses CSV and sends sync_hardware_csv without local toggle_connection
    csv_path = tmp_path / "ui_import.csv"
    csv_path.write_text("intersection_id,ip_address\nJ5,10.0.0.99\n", encoding="utf-8")
    mock_mgr = MagicMock()
    mock_mgr.saved_ips = {}
    mock_mgr.active_connections = {}
    mock_mgr.saved_snmp_configs = {}
    hw_handler = HardwareSettingsHandler(mock_mgr, settings_client=settings_client, locale_manager=_FakeLocale())
    hw_handler._on_import_result(SimpleNamespace(files=[SimpleNamespace(path=str(csv_path))]))

    mock_mgr.import_csv_config.assert_not_called()
    assert mock_mgr.saved_ips["J5"] == "10.0.0.99"
    sent_types = [c.args[0] for c in settings_client.send_command.call_args_list]
    assert "sync_hardware_csv" in sent_types


def test_failsafe_and_traffic_frame_processor_owner_flow():
    driver = MagicMock()
    driver.is_connected = True
    driver.get_status.return_value = {"status": "online", "active_greens": 1}
    conn_mgr = MagicMock()
    conn_mgr.active_connections = {"J1": driver}
    conn_mgr.export_hardware_status_snapshot.return_value = {
        "J1": {"is_connected": True, "brand": "B", "model": "M", "protocol": "NTCIP 1202", "ip_address": "1.2.3.4"}
    }
    go_client = MagicMock()
    go_client.is_running.return_value = True

    ai_pipe = MagicMock()
    ai_pipe.closed = False
    sds_q = queue.Queue()

    coord = HardwareGatewayCoordinator(
        sds_data_queue=sds_q,
        ai_pipe_conn=ai_pipe,
        connection_manager=conn_mgr,
        go_client=go_client,
        evp_service=SimpleNamespace(export_remote_snapshot=lambda: {"vehicles": {}, "active_preemptions": {}}),
    )
    coord.refresh_snapshots(push_to_sds=False)

    # TrafficFrameProcessor attaches cached hardware telemetry/status onto hft_step
    failsafe = FailsafeManager(
        ai_pipe_conn=ai_pipe,
        monitor_client=MagicMock(locale_manager=_FakeLocale()),
        locale_manager=_FakeLocale(),
    )
    failsafe.hardware_gateway_coordinator = coord
    tfp = TrafficFrameProcessor(
        ai_pipe_conn=ai_pipe,
        watchdog_queue=queue.Queue(),
        sds_data_queue=sds_q,
        failsafe_manager=failsafe,
        topology_manager=MagicMock(agent_maturity_cache={}, tls_phases_cache={}),
        telemetry_aggregator=MagicMock(should_update=MagicMock(return_value=False)),
        override_manager=MagicMock(active_street_overrides={}),
        locale_manager=_FakeLocale(),
    )
    tfp.hardware_gateway_coordinator = coord
    tfp.process_traffic_frame(SimpleNamespace(timestamp=5.0, sequence_id=1, edges={}))

    sent_step = ai_pipe.send.call_args[0][0]
    assert sent_step[0] == "custom" and sent_step[1] == "hft_step"
    assert sent_step[2][0]["tls_telemetry"]["J1"]["active_greens"] == 1
    assert sent_step[2][0]["hardware_status"]["J1"]["brand"] == "B"

    # Failsafe trigger releases driver via release_hold and alerts AI process
    failsafe._notify_hardware_failsafe()
    driver.apply_action.assert_called_with({"action_type": "release_hold"})
    go_client.emergency_release_all.assert_called_once()
    ai_pipe.send.assert_any_call(("hardware", "failsafe_state", (True,), {}))


# =========================================================================
# PHASE 3: F.E.N.I.X. POST-RESURRECTION RECONCILE + HANDOVER ROUNDTRIP
# =========================================================================


def test_fenix_post_resurrection_stage_reconciliation_and_handover_complete():
    ctrl_conn, ai_conn = Pipe(duplex=True)
    ui_q = queue.Queue()
    fenix_q = queue.Queue()
    sds_q = queue.Queue()

    try:
        # 1. ProcessManager._fenix_supervision_loop resurrects AI and signals CentralController via ui_q
        pm = ProcessManager.__new__(ProcessManager)
        pm.queues = {"ui": ui_q, "fenix": fenix_q}
        pm._stop_fenix_supervision = MagicMock()
        pm._stop_fenix_supervision.is_set.side_effect = [False, False, False, True]
        pm.fenix_supervisor = MagicMock()
        pm.fenix_supervisor.resurrect_ai.return_value = True
        pm.fenix_supervisor.runner = SimpleNamespace(_process=SimpleNamespace(pid=4321, name="AI_Process"))
        pm.p_ai = None
        pm.processes = []

        fenix_q.put(("TRIGGER_RESURRECTION", "heartbeat_timeout"))

        # 2. CentralController Coordinator decodes field stage 2 from NTCIP telemetry for J1 & uses cache for J2
        driver_j1 = MagicMock()
        driver_j1.is_connected = True
        driver_j1.green_stages = [0, 2]
        driver_j1.stage_states = {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}
        driver_j1.get_status.return_value = {
            "status": "online",
            "protocol": "NTCIP 1202",
            "active_greens": 12,  # Stage 2 ('rrGG')
        }
        owner_conn_mgr = MagicMock()
        owner_conn_mgr.active_connections = {"J1": driver_j1}
        topology_mgr = SimpleNamespace(tls_phases_cache={"J1": 0, "J2": 3}, agent_maturity_cache={})

        coordinator = HardwareGatewayCoordinator(
            sds_data_queue=sds_q,
            ai_pipe_conn=ctrl_conn,
            topology_manager=topology_mgr,
            fenix_queue=fenix_q,
            connection_manager=owner_conn_mgr,
            go_client=MagicMock(),
            evp_service=MagicMock(),
        )
        with patch("src.controller.request_processor.SecurityManager"):
            req_proc = RequestProcessor(
                settings=configparser.ConfigParser(),
                ai_pipe_conn=ctrl_conn,
                watchdog_q=queue.Queue(),
                health_monitor=MagicMock(),
                sds_data_queue=sds_q,
                sas_data_queue=queue.Queue(),
                ui_command_queue=ui_q,
                locale_manager=_FakeLocale(),
                override_manager=MagicMock(is_ai_command_blocked=MagicMock(return_value=False)),
                failsafe_manager=MagicMock(),
                topology_manager=topology_mgr,
            )
        req_proc.hardware_gateway_coordinator = coordinator
        req_proc.ai_handler.hardware_gateway_coordinator = coordinator

        # Run ProcessManager loop until TRIGGER_RESURRECTION enqueues fenix_post_resurrection on ui_q
        pm._stop_fenix_supervision.is_set.side_effect = [False, False, True]
        pm._fenix_supervision_loop()
        assert ui_q.qsize() == 1

        # 3. RequestProcessor consumes fenix_post_resurrection -> dispatches reconcile_stages over ctrl_conn
        req_proc.process_queues(sumo_conn=None, is_ai_healthy=True)
        assert ai_conn.poll(0.5)
        reconcile_cmd = ai_conn.recv()
        assert reconcile_cmd[0] == "fenix" and reconcile_cmd[1] == "reconcile_stages"
        stages_map = reconcile_cmd[2][0]
        assert stages_map["J1"] == 2  # Decoded live field stage!
        assert stages_map["J2"] == 3  # Topology cache fallback!

        # 4. AI_Process EventRouter receives reconcile_stages into StateReconciler
        def _send_handover():
            ai_conn.send(("fenix_handover_complete", {"ok": True}))

        reconciler = StateReconciler(on_handover_complete=_send_handover)
        extractor = SimpleNamespace(
            tl_green_stages={"J1": [0, 2]},
            tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr", 2: "rrGG", 3: "rryy"}},
        )
        step_proc = StepProcessor(
            settings=configparser.ConfigParser(),
            locale_manager=_FakeLocale(),
            step_timer=StepTimer(),
            agent_evaluator=MagicMock(
                evaluate_fleet=MagicMock(
                    return_value=SimpleNamespace(
                        actions={"J1": 1},
                        lanes_state={},
                        maturity_info={},
                        step_reward_sum=0.0,
                        metrics_delta={},
                        guardian_vetoed_any=False,
                    )
                )
            ),
            stage_transition_manager=MagicMock(),
            action_supervisor=MagicMock(
                connection_manager=MagicMock(active_connections={}), _last_stage_change_time={}
            ),
            online_pae_trainer=MagicMock(),
            mfd_processor=MagicMock(process_step=MagicMock(return_value={})),
            hardware_actuator=MagicMock(),
            telemetry_publisher=StepTelemetryPublisher(pipe_conn=ai_conn),
            cycle_manager=MagicMock(),
            episode_reporter=MagicMock(),
            state_reconciler=reconciler,
            state_extractor=extractor,
        )
        step_proc.log_step_progress = False
        trainer = SimpleNamespace(
            state_reconciler=reconciler, agents={"J1": MagicMock(), "J2": MagicMock()}, is_running=True
        )
        event_router = EventRouter(
            pipe_conn=ai_conn, trainer_instance=trainer, agent_manager=MagicMock(), step_processor=step_proc
        )

        event_router._execute_command(reconcile_cmd[0], reconcile_cmd[1], reconcile_cmd[2])
        assert reconciler.is_inference_allowed("J1") is False
        assert reconciler.is_inference_allowed("J2") is False
        assert reconciler.is_all_unfrozen() is False

        # 5. Field hardware advances to yellow/next stage (J1 -> stage 3, J2 -> stage 0) -> unfreezes AI & notifies CentralController
        step_proc.set_current_phases({"J1": 2, "J2": 3})
        step_proc.process_hft_step(
            {
                "timestamp": 10.0,
                "sequence_id": 1,
                "edges": {},
                "tls_telemetry": {
                    "J1": {"status": "online", "protocol": "NTCIP 1202", "active_greens": 0, "active_yellows": 12},
                    "J2": {"status": "online", "protocol": "NTCIP 1202", "current_stage": 1},
                },
            },
            trainer.agents,
        )
        assert reconciler.is_inference_allowed("J1") is True
        assert reconciler.is_inference_allowed("J2") is True
        assert reconciler.is_all_unfrozen() is True

        # Drain AI pipe msgs on ctrl_conn until fenix_handover_complete arrives, process in AIRequestHandler
        received_handover = False
        while ctrl_conn.poll(0.2):
            msg = ctrl_conn.recv()
            req_proc.ai_handler.process(msg, sumo_conn=None, ai_pipe_conn=ctrl_conn, override_commands_buffer=[])
            if isinstance(msg, tuple) and msg[0] == "fenix_handover_complete":
                received_handover = True

        assert received_handover is True

        # 6. ProcessManager consumes HANDOVER_COMPLETE -> confirm_handover_complete()
        pm._stop_fenix_supervision.is_set.side_effect = [False, False, True]
        pm._fenix_supervision_loop()
        pm.fenix_supervisor.confirm_handover_complete.assert_called_once()
    finally:
        ctrl_conn.close()
        ai_conn.close()
