# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Architectural contract tests and targeted collaborator unit tests verifying the
SOLID + Clean Architecture decomposition across all files previously >= 300 lines.
"""

import ast
import configparser
import os
import queue
import sqlite3
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import torch

from src.agents.agent_checkpoint_manager import AgentCheckpointManager
from src.agents.local_agent import LocalAgent
from src.controller.connection_operation_handler import _DefaultTrafficDriverFactory
from src.controller.evp_fleet_command_handler import EvpFleetCommandHandler
from src.controller.frame_sanitizer import FrameSanitizer
from src.controller.hardware_override_dispatcher import HardwareOverrideDispatcher
from src.controller.sds_frame_publisher import SDSFramePublisher
from src.drivers.remote_gateway_backend import RemoteGatewayBackend
from src.drivers.remote_hardware_driver import RemoteHardwareDriverProxy
from src.drivers.remote_proxy_synchronizer import sync_remote_driver_proxies
from src.engine.action_supervisor import ActionSupervisor
from src.engine.action_veto_resolver import ActionVetoResolver
from src.engine.batched_pae_encoder import BatchedPAEEncoder
from src.engine.physical_action_masker import PhysicalActionMasker
from src.evp.application.evp_snapshot_synchronizer import EVPSnapshotSynchronizer
from src.evp.evp_models import CorporationType, EmergencyVehicle
from src.interfaces import (
    IActionSupervisor,
    IBatchedPAEEncoder,
    IConnectionConfigCSVStorage,
    IConnectionConfigRepository,
    IGatewaySettingsPersister,
    IPhysicalActionMasker,
    IRemoteGatewayBackend,
    ITrafficDriverFactory,
)
from src.repositories.connection_csv_store import ConnectionCSVStore
from src.repositories.hardware_connection_repo import HardwareConnectionRepository
from ui.controllers.remote_gateway_settings_persister import RemoteGatewaySettingsPersister

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _collected_imports(filepath: str) -> set[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
            imports.add(node.module)
    return imports


def test_all_source_files_strictly_below_300_lines():
    """Enforces < 300 line modularization budget across all production Python and Go sources."""
    oversized = []
    for root_dir in ("src", "ui", "src_go"):
        base = os.path.join(PROJECT_ROOT, root_dir)
        for cur_dir, _, filenames in os.walk(base):
            if "__pycache__" in cur_dir:
                continue
            for fname in filenames:
                if not fname.endswith((".py", ".go")):
                    continue
                full_path = os.path.join(cur_dir, fname)
                with open(full_path, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                if line_count >= 300:
                    rel = os.path.relpath(full_path, PROJECT_ROOT)
                    oversized.append((rel, line_count))
    assert oversized == [], f"Production source files >= 300 lines detected: {oversized}"


def test_clean_architecture_facade_dependency_hygiene():
    """Verifies decomposed facades keep UI/controller layers free of subprocess and raw SQL coupling."""
    rg_ctrl = os.path.join(PROJECT_ROOT, "ui", "controllers", "remote_gateway_controller.py")
    rg_imports = _collected_imports(rg_ctrl)
    assert "subprocess" not in rg_imports
    assert "json" not in rg_imports
    assert "src.drivers.go_gateway_client" not in rg_imports

    repo_facade = os.path.join(PROJECT_ROOT, "src", "controller", "connection_config_repo.py")
    op_handler = os.path.join(PROJECT_ROOT, "src", "controller", "connection_operation_handler.py")
    for path in (repo_facade, op_handler):
        imps = _collected_imports(path)
        assert "sqlite3" not in imps
        assert "psycopg2" not in imps
        assert "src.database.db_engine" not in imps
        assert "database.db_engine" not in imps

    helpers_facade = os.path.join(PROJECT_ROOT, "src", "utils", "local_agent_helpers.py")
    with open(helpers_facade, "r", encoding="utf-8") as f:
        assert len(f.readlines()) < 50


def test_new_protocols_runtime_conformance():
    """Checks structural runtime conformance of all newly introduced SOLID ports and adapters."""
    assert isinstance(RemoteGatewayBackend(go_client=MagicMock()), IRemoteGatewayBackend)
    assert isinstance(RemoteGatewaySettingsPersister(), IGatewaySettingsPersister)
    assert isinstance(ConnectionCSVStore(), IConnectionConfigCSVStorage)
    assert isinstance(HardwareConnectionRepository(engine=MagicMock()), IConnectionConfigRepository)
    assert isinstance(_DefaultTrafficDriverFactory(), ITrafficDriverFactory)
    assert isinstance(
        PhysicalActionMasker(state_extractor=MagicMock(), action_supervisor=MagicMock()), IPhysicalActionMasker
    )
    assert isinstance(BatchedPAEEncoder(), IBatchedPAEEncoder)

    lm = MagicMock()
    lm.get_string.return_value = "ok"
    sup = ActionSupervisor(
        connection_manager=MagicMock(),
        settings=configparser.ConfigParser(),
        state_extractor=MagicMock(),
        locale_manager=lm,
    )
    assert isinstance(sup, IActionSupervisor)


def test_physical_action_masker_and_veto_resolver(tmp_path):
    """Verifies PhysicalActionMasker uses IActionSupervisor and ActionVetoResolver unifies EVP/Guardian vetoes."""
    agent = LocalAgent(
        "J1", n_observations=6, initial_hyperparams={}, log_dir=str(tmp_path), locale_manager=MagicMock()
    )

    class _SupervisorStub:
        def get_last_stage_change_time(self, tl_id: str, default: float = 0.0) -> float:
            return 20.0 if tl_id == "J1" else default

    se = SimpleNamespace(tl_stage_codes={"J1": {0: "GGrr", 1: "yyrr"}})
    masker = PhysicalActionMasker(state_extractor=se, action_supervisor=_SupervisorStub())
    mask = masker.compute_mask("J1", agent, current_stage_idx=1, sim_time=25.0)
    assert mask is not None
    raw_mask = mask.tolist() if hasattr(mask, "tolist") else np.asarray(mask._data).tolist()
    assert raw_mask == [[False, True]]

    mock_agent = MagicMock()
    mock_agent.device = torch.device("cpu")
    eval_log_prob = MagicMock()
    mock_agent.evaluate.return_value = (eval_log_prob, None, None)

    resolver = ActionVetoResolver(state_extractor=se, action_supervisor=MagicMock(_last_stage_change_time={"J1": 10.0}))
    act_int, act_idx, log_prob, is_auth, reason, vetoed = resolver.resolve(
        tl_id="J1",
        agent=mock_agent,
        guardian=None,
        current_stage_idx=0,
        sim_time=20.0,
        state_vector=np.zeros(6, dtype=np.float32),
        state_tensor=torch.zeros(1, 1, 6),
        precomputed_pae_latent=None,
        action_int=0,
        action_idx=torch.tensor([0]),
        action_log_prob=torch.tensor([-0.1]),
        is_auth=True,
        reason="ok",
        evp_override="SAMU:VTR-01",
    )
    assert vetoed is True
    assert is_auth is False
    assert act_int == 1
    assert act_idx is not None
    assert "VTR-01" in reason
    assert log_prob is eval_log_prob


def test_batched_pae_encoder_with_mock_pae():
    """Verifies BatchedPAEEncoder batches valid traffic lights and returns per-intersection latents."""
    encoder = BatchedPAEEncoder()
    shared_pae = MagicMock()
    shared_pae.device = torch.device("cpu")
    shared_pae.encode.return_value = torch.tensor([[1.0, 2.0], [3.0, 4.0]])

    agents = {
        "J1": SimpleNamespace(shared_pae=shared_pae),
        "J2": SimpleNamespace(shared_pae=shared_pae),
    }
    pre_states = {
        "J1": (np.zeros(4), torch.zeros(1, 4), np.zeros(4)),
        "J2": (np.zeros(4), torch.zeros(1, 4), np.zeros(4)),
    }
    latents = encoder.encode_fleet(agents, pre_states)
    assert set(latents.keys()) == {"J1", "J2"}
    shared_pae.encode.assert_called_once()


def test_frame_sanitizer_and_sds_frame_publisher():
    """Verifies FrameSanitizer anomaly sanitization and SDSFramePublisher fast/slow queue emission."""
    assert FrameSanitizer.sanitize_timestamp(-5.0) == 0.0
    assert FrameSanitizer.sanitize_sequence_id("bad") == 0

    override_mgr = SimpleNamespace(active_street_overrides={"-edge1": "BLOCKED"})
    frame = SimpleNamespace(
        timestamp=2.5,
        sequence_id=7,
        edges={"edge1": {"occupancy": 0.9, "mean_speed": 10.0, "queue_length": 5.0}},
    )
    edges = FrameSanitizer.build_clean_edges(frame, override_mgr)
    assert edges["edge1"] == {"occupancy": 0.0, "mean_speed": 0.0, "queue_length": 0.0}

    sds_q: queue.Queue = queue.Queue()
    topo = SimpleNamespace(
        agent_maturity_cache={"J1": "ADULT"}, tls_phases_cache={"J1": 1}, try_restore_state=MagicMock()
    )
    agg = MagicMock()
    agg.should_update.return_value = True
    agg.compute_rich_payload.return_value = {"timestamp": 2.5, "edges": {}}
    coord = SimpleNamespace(get_cached_hardware_status=lambda: {"J1": {"is_connected": True}})

    pub = SDSFramePublisher(
        sds_data_queue=sds_q,
        topology_manager=topo,
        telemetry_aggregator=agg,
        get_string_fn=lambda k, default="", **_: default,
    )
    pub.publish(frame, current_time=2.5, coordinator=coord)
    items = [sds_q.get_nowait(), sds_q.get_nowait()]
    assert items[0][0] == "hft_rich_update"
    assert items[1][1]["hardware_status"] == {"J1": {"is_connected": True}}


def test_evp_snapshot_synchronizer_and_command_handlers():
    """Verifies EVPSnapshotSynchronizer roundtrip, EvpFleetCommandHandler, and HardwareOverrideDispatcher."""
    veh = EmergencyVehicle(
        vehicle_id="AMB-77", corporation=CorporationType.SAMU, latitude=-1.0, longitude=-2.0, siren_active=True
    )
    veh.last_update_time = time.time()
    preempt_engine = SimpleNamespace(_active_preemptions={"J1": {"vehicle_id": "AMB-77", "start_time": 12.0}})
    snap = EVPSnapshotSynchronizer.export_snapshot({"AMB-77": veh}, preempt_engine)

    dst_vehicles = {}
    dst_engine = SimpleNamespace(_active_preemptions={})
    EVPSnapshotSynchronizer.apply_snapshot(snap, dst_vehicles, dst_engine, offline_timeout_seconds=30.0)
    assert "AMB-77" in dst_vehicles
    assert "J1" in dst_engine._active_preemptions

    evp_svc = MagicMock()
    evp_svc.unregister_fleet_vehicle.return_value = True
    go_client = MagicMock()
    go_client.is_running.return_value = True
    go_client.send_command.return_value = {"success": True}
    fleet_handler = EvpFleetCommandHandler(lambda _c: evp_svc, lambda _c: go_client, lambda _b: None)
    assert (
        fleet_handler.set_evp_fleet(
            {"action": "register", "vehicle": {"vehicle_id": "BOM-1", "corporation": "BOMBEIROS"}}
        )
        is True
    )
    assert fleet_handler.set_evp_fleet({"action": "unregister", "vehicle_id": "BOM-1"}) is True
    assert fleet_handler.execute_ai_evp_preempt({"intersection_id": "J1", "action_data": {"stage": 2}}) is True

    drv = MagicMock(is_connected=True, intersection_id="J1")
    conn_mgr = SimpleNamespace(active_connections={"J1": drv})
    override_disp = HardwareOverrideDispatcher(lambda _c: conn_mgr, lambda _c: go_client)
    override_disp.on_failsafe_triggered()
    drv.apply_action.assert_called_with({"action_type": "release_hold"})
    go_client.emergency_release_all.assert_called_once()


def test_agent_checkpoint_manager_injected_vault_repo(tmp_path):
    """Verifies AgentCheckpointManager accepts injected ICloudVaultRepository without DB fallback."""
    agent = LocalAgent(
        "J_VAULT", n_observations=6, initial_hyperparams={}, log_dir=str(tmp_path), locale_manager=MagicMock()
    )
    vault_repo = MagicMock()
    ckpt_path = str(tmp_path / "agent.pth")
    ckpt_payload = {
        "n_observations": 6,
        "maturity_stage": "ADULT",
        "policy_net_state_dict": None,
        "episodes_done": 3,
        "steps_done": 42,
        "xai_memory": None,
    }

    with patch("torch.save") as mock_save, patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        AgentCheckpointManager.save(agent, ckpt_path, "ADULT", vault_repo=vault_repo)
    mock_save.assert_called_once()
    vault_repo.sync_file_to_vault.assert_called_once()

    vault_repo.restore_file_from_vault.return_value = True
    with (
        patch("torch.load", return_value=ckpt_payload),
        patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)),
    ):
        maturity = AgentCheckpointManager.load(agent, ckpt_path, vault_repo=vault_repo)
    assert maturity == "ADULT"
    assert agent.episodes_done == 3
    vault_repo.restore_file_from_vault.assert_called_once()


def test_hardware_connection_repository_and_csv_store_sqlite_roundtrip(tmp_path):
    """Verifies HardwareConnectionRepository & ConnectionCSVStore directly over SQLite + CSV."""
    db_file = str(tmp_path / "conn_repo.db")
    csv_file = str(tmp_path / "connections.csv")

    class _SQLiteEngine:
        db_type = "sqlite"

        @staticmethod
        def get_connection():
            conn = sqlite3.connect(db_file)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS hardware_controller_connections "
                "(intersection_id TEXT PRIMARY KEY, ip_address TEXT, "
                "auto_connect BOOLEAN DEFAULT TRUE, last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP, snmp_config TEXT)"
            )
            conn.commit()
            return conn

    repo = HardwareConnectionRepository(engine=_SQLiteEngine())
    assert repo.save_connection_db("J1", "10.0.0.10:161", snmp_config={"community": "public"}) is True
    assert repo.load_all_connections_db() == {"J1": "10.0.0.10:161"}
    assert repo.load_all_snmp_configs_db() == {"J1": {"community": "public"}}
    assert repo.remove_connection_db("J1") is True
    assert repo.load_all_connections_db() == {}

    csv_store = ConnectionCSVStore()
    assert csv_store.export_csv_template(csv_file, {"J2": "10.0.0.20:161"}, ["J2"]) is True
    parsed = csv_store.import_csv_config(csv_file)
    assert parsed == {"J2": "10.0.0.20:161"}


def test_remote_proxy_synchronizer_lifecycle():
    """Verifies RemoteProxySynchronizer materializes, updates, and prunes proxies under remote role."""
    conn_mgr = SimpleNamespace(active_connections={})
    extractor = SimpleNamespace(tl_green_stages={"J1": [0, 2]}, tl_stage_codes={"J1": {0: "GGrr", 2: "rrGG"}})

    with patch("src.drivers.go_gateway_client.GoGatewayClient.is_remote_gateway_role", return_value=True):
        disconnected = sync_remote_driver_proxies(
            conn_mgr=conn_mgr,
            hardware_status={"J1": {"is_connected": True, "ip_address": "10.0.0.5"}},
            state_extractor=extractor,
            prune_missing=True,
        )
        assert disconnected == []
        assert isinstance(conn_mgr.active_connections["J1"], RemoteHardwareDriverProxy)
        assert conn_mgr.active_connections["J1"].green_stages == [0, 2]

        disconnected = sync_remote_driver_proxies(conn_mgr=conn_mgr, hardware_status={}, prune_missing=True)
        assert disconnected == ["J1"]
        assert "J1" not in conn_mgr.active_connections
