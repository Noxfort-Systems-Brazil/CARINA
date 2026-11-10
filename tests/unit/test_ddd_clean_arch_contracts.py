# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Architectural Contract Tests (DDD + Clean Architecture + SOLID).
Validates layer boundaries, type identity unification, interface segregation (ISP),
and Dependency Inversion (DIP) via ServiceContainer.
"""

import ast
import configparser
import os
from unittest.mock import MagicMock

from src.central_controller import CentralController
from src.controller.common_types import SignalState as CommonSignalState
from src.controller.common_types import StageDefinition as CommonStageDefinition
from src.controller.intersection_state_manager import IntersectionState as ManagerIntersectionState
from src.controller.stage_definition import StageDefinition as LegacyStageDefinition
from src.controller.topology_loader import IntersectionData as LoaderIntersectionData
from src.controller.topology_manager import (
    ControllerTopologyCoordinator,
    TopologyManager as ControllerTopoAlias,
)
from src.domain import (
    AgentMaturity,
    CorporationType,
    EmergencyVehicle,
    FenixState,
    FleetDecisions,
    IntersectionData,
    IntersectionState,
    Maturity,
    MaturityConfig,
    RegisteredVehicle,
    SecurityEvent,
    SignalState,
    StageDefinition,
    TelemetryData,
    User,
    UserRole,
)
from src.engine.agent_evaluator import FleetDecisions as EvaluatorFleetDecisions
from src.factories import CentralControllerContainer, EngineFactory, ServiceContainer
from src.interfaces import (
    IAgentCheckpointRepository,
    ICloudVaultRepository,
    IFailsafeManager,
    IFluidDynamicsMaintenance,
    IFluidDynamicsReader,
    IFluidDynamicsRepository,
    IFluidDynamicsWriter,
    IMaturityRepository,
    ISimulationRepository,
    IStepDecisionRepository,
    ITopologyCoordinator,
)
from src.manager.agent_checkpoint_repository import AgentCheckpointRepository
from src.manager.agent_population_loader import (
    AgentPopulationLoader,
    TopologyManager as ManagerTopoAlias,
)
from src.manager.topology_manager import TopologyManager as LegacyManagerTopoAlias
from src.repositories.cloud_vault_repo import CloudVaultRepository
from src.repositories.fluid_dynamics_repo import FluidDynamicsRepository
from src.repositories.maturity_state_repository import MaturityStateRepository
from src.repositories.simulation_repo import SimulationRepository
from src.repositories.step_decision_repo import StepDecisionRepository


def test_domain_value_objects_and_entities_identity_unification():
    """Ensures StageDefinition and other domain types are unified across all import paths."""
    assert StageDefinition is CommonStageDefinition
    assert StageDefinition is LegacyStageDefinition
    assert SignalState is CommonSignalState
    assert IntersectionState is ManagerIntersectionState
    assert IntersectionData is LoaderIntersectionData
    assert FleetDecisions is EvaluatorFleetDecisions

    stage = StageDefinition(state_string="GGrr", yellow_string="yyrr", all_red_string="rrrr")
    assert isinstance(stage, CommonStageDefinition)
    assert isinstance(stage, LegacyStageDefinition)

    # Verify rich domain entities are exposed from src.domain
    agent = AgentMaturity(agent_id="tls_1", phase=Maturity.CHILD)
    agent.record_episode(-120.5)
    assert agent.episodes_in_phase == 1

    ev = EmergencyVehicle(
        vehicle_id="SAMU-01",
        corporation=CorporationType.SAMU,
        latitude=-23.31,
        longitude=-51.16,
        siren_active=True,
    )
    ev.activate_evp("tls_1", "block_A")
    assert ev.is_evp_triggered is True
    assert "tls_1" in ev.active_intersections


def test_ubiquitous_language_topology_managers_disambiguated():
    """Ensures the two distinct TopologyManagers have explicit domain names while keeping legacy aliases."""
    assert ControllerTopologyCoordinator is ControllerTopoAlias
    assert AgentPopulationLoader is ManagerTopoAlias
    assert LegacyManagerTopoAlias is AgentPopulationLoader
    assert ControllerTopologyCoordinator is not AgentPopulationLoader


def test_clean_architecture_dependency_rule_zero_ui_or_infra_in_domain_and_interfaces():
    """
    Verifies the Clean Architecture Dependency Rule:
    src/domain/ and src/interfaces/ must NOT import PyQt6, psycopg2, grpc, sumolib, or torch.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    forbidden_roots = {"PyQt6", "psycopg2", "grpc", "sumolib", "torch", "sqlalchemy"}

    for layer in ("domain", "interfaces"):
        layer_dir = os.path.join(project_root, "src", layer)
        for root, _, files in os.walk(layer_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=fpath)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top_pkg = alias.name.split(".")[0]
                            assert top_pkg not in forbidden_roots, (
                                f"Dependency Rule violation in {fpath}: imports '{alias.name}'"
                            )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        top_pkg = node.module.split(".")[0]
                        assert top_pkg not in forbidden_roots, (
                            f"Dependency Rule violation in {fpath}: imports from '{node.module}'"
                        )


def test_repository_ports_structural_conformance_isp():
    """Verifies that concrete repositories satisfy segregated Protocol ports in src/interfaces/."""
    mock_engine = MagicMock()
    mock_engine.get_connection.return_value = None
    mock_locale = MagicMock()

    fluid_repo = FluidDynamicsRepository(mock_engine, mock_locale)
    assert isinstance(fluid_repo, IFluidDynamicsReader)
    assert isinstance(fluid_repo, IFluidDynamicsWriter)
    assert isinstance(fluid_repo, IFluidDynamicsMaintenance)
    assert isinstance(fluid_repo, IFluidDynamicsRepository)

    # Sub-components also satisfy their narrow ISP ports directly
    assert isinstance(fluid_repo.reader, IFluidDynamicsReader)
    assert isinstance(fluid_repo.writer, IFluidDynamicsWriter)
    assert isinstance(fluid_repo.maintenance, IFluidDynamicsMaintenance)

    sim_repo = SimulationRepository(mock_engine, mock_locale)
    assert isinstance(sim_repo, ISimulationRepository)

    step_repo = StepDecisionRepository(mock_engine, mock_locale)
    assert isinstance(step_repo, IStepDecisionRepository)

    vault_repo = CloudVaultRepository(mock_engine, mock_locale)
    assert isinstance(vault_repo, ICloudVaultRepository)

    maturity_repo = MaturityStateRepository()
    assert isinstance(maturity_repo, IMaturityRepository)

    assert isinstance(AgentCheckpointRepository, IAgentCheckpointRepository)


def test_central_controller_dependency_injection_via_service_container():
    """Verifies DIP: CentralController accepts pre-built injected collaborators without side effects."""
    assert ServiceContainer is CentralControllerContainer
    assert EngineFactory is not None

    config = configparser.ConfigParser()
    config.add_section("WATCHDOG")
    config.set("WATCHDOG", "heartbeat_timeout_seconds", "5.0")

    injected_services = {
        "override_manager": MagicMock(),
        "telemetry_aggregator": MagicMock(),
        "health_monitor": MagicMock(),
        "monitor_client": MagicMock(),
        "failsafe_manager": MagicMock(spec=IFailsafeManager),
        "topology_manager": MagicMock(spec=ITopologyCoordinator),
        "db_manager": None,
        "traffic_data_recorder": None,
        "traffic_frame_processor": MagicMock(),
        "yellow_schedule_manager": MagicMock(),
        "request_processor": MagicMock(),
        "readiness_latch": MagicMock(),
        "topology_recorder_bridge": MagicMock(),
        "hft_system_facade": MagicMock(),
        "grpc_server_manager": MagicMock(),
        "hft_event_loop": MagicMock(),
    }

    cc = CentralController(
        settings=config,
        ai_pipe_conn=MagicMock(),
        watchdog_queue=MagicMock(),
        sds_data_queue=MagicMock(),
        sas_data_queue=MagicMock(),
        ui_command_queue=MagicMock(),
        locale_manager=MagicMock(),
        services=injected_services,
    )

    assert cc.failsafe_manager is injected_services["failsafe_manager"]
    assert cc.topology_manager is injected_services["topology_manager"]
    assert cc.request_processor is injected_services["request_processor"]
    cc.failsafe_manager.set_failsafe_timeout.assert_called_once_with(5.0)
    cc.topology_manager.try_restore_state.assert_called_once()
