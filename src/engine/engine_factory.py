# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import types
from multiprocessing.connection import Connection
from typing import Any, Optional

import torch

from controller.connection_manager import HardwareConnectionManager
from core.action_authorizer import ActionAuthorizer
from core.episode_reporter import EpisodeReporter
from drivers.hardware_stage_actuator import HardwareStageActuator
from engine.action_supervisor import ActionSupervisor
from engine.agent_evaluator import AgentEvaluator
from engine.batched_pae_encoder import BatchedPAEEncoder
from engine.event_router import EventRouter
from engine.hardware_telemetry_synchronizer import HardwareTelemetrySynchronizer
from engine.input_preprocessor import InputPreprocessor
from engine.online_pae_trainer import OnlinePAETrainer
from engine.physical_action_masker import PhysicalActionMasker
from engine.reward_computer import RewardComputer
from engine.scenario_loader import ScenarioLoader
from engine.state_extractor import StateExtractor
from engine.step_processor import StepProcessor
from engine.step_telemetry_publisher import StepTelemetryPublisher
from engine.step_timer import StepTimer
from engine.strategic_coordinator import StrategicCoordinator
from engine.trainer import Trainer
from manager.agent_manager import AgentManager
from manager.agent_population_loader import AgentPopulationLoader as TopologyManager
from manager.cycle_manager import CycleManager
from manager.stage_transition_manager import StageTransitionManager
from maturity.maturity_manager import MaturityManager
from mfd.mfd import MacroscopicFundamentalDiagram
from mfd.mfd_processor import MFDProcessor
from safety.guardian_shadow_trainer import GuardianShadowTrainer
from utils.locale_manager_backend import LocaleManagerBackend


class EngineFactory:
    """
    Composition Root for CARINA's AI Engine.
    Instantiates and connects all specialized collaborators into a coherent runtime graph.
    """

    @classmethod
    def create_trainer(
        cls,
        settings: configparser.ConfigParser,
        log_dir: str,
        gpu_info: str,
        pipe_conn: Connection,
        project_root: Optional[str] = None,
    ) -> Trainer:
        """
        Assembles all AI Engine collaborators and constructs a fully wired Trainer instance.
        """
        if project_root is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        locale_manager = LocaleManagerBackend()
        sequence_length = settings.getint("AI_TRAINING", "sequence_length", fallback=12)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 1. Hardware & Perceptual Abstraction
        connection_manager = HardwareConnectionManager()
        state_extractor = StateExtractor(locale_manager)
        action_supervisor = ActionSupervisor(
            connection_manager=connection_manager,
            settings=settings,
            state_extractor=state_extractor,
            locale_manager=locale_manager,
        )
        action_authorizer = ActionAuthorizer(settings=settings, locale_manager=locale_manager)
        hardware_actuator = HardwareStageActuator()

        # 2. AI Core & Supervision
        population_proxy = types.SimpleNamespace(agents={}, n_actions=2)
        agent_manager = AgentManager(settings=settings, device=device, project_root=project_root)
        input_preprocessor = InputPreprocessor(sequence_length=sequence_length, device=device)
        maturity_manager = MaturityManager(
            settings=settings, locale_manager=locale_manager, population_manager=population_proxy
        )
        reward_computer = RewardComputer(settings=settings, state_extractor=state_extractor)
        online_pae_trainer = OnlinePAETrainer(settings=settings, agent_manager=agent_manager)

        # 3. Database Manager (Safe Fallback)
        try:
            from database.database_manager import DatabaseManager

            db_manager = DatabaseManager(locale_manager)
            db_manager.start_operation_session()
        except Exception as e_db:
            db_manager = None
            logging.warning(f"[EngineFactory] Could not initialize DatabaseManager: {e_db}", exc_info=True)

        # 4. Metrics & Network Performance
        topology_manager = TopologyManager(settings=settings, locale_manager=locale_manager, log_dir=log_dir)
        guardian_shadow_trainer = GuardianShadowTrainer(settings=settings, device=device)
        cycle_manager = CycleManager(
            maturity_manager=maturity_manager,
            pipe_conn=pipe_conn,
            settings=settings,
            guardian_trainer=guardian_shadow_trainer,
        )
        mfd = MacroscopicFundamentalDiagram()
        mfd_processor = MFDProcessor(mfd=mfd, state_extractor=state_extractor)
        episode_reporter = EpisodeReporter(locale_manager=locale_manager, maturity_manager=maturity_manager)

        # 5. FENIX State Reconciler
        try:
            from fenix.state_reconciler import StateReconciler

            def _on_fenix_handover_complete() -> None:
                if pipe_conn is not None and getattr(pipe_conn, "closed", False) is not True:
                    try:
                        pipe_conn.send(("fenix_handover_complete", {}))
                    except Exception as exc:
                        logging.debug(f"[EngineFactory] Failed sending fenix_handover_complete: {exc}")

            state_reconciler = StateReconciler(on_handover_complete=_on_fenix_handover_complete)
        except Exception:
            state_reconciler = None

        # 5.1 EVP Bridge remote IPC & stage metadata wiring
        try:
            from drivers.go_gateway_client import GoGatewayClient

            if GoGatewayClient.is_remote_gateway_role():
                from evp.evp_bridge import EVPBridge

                def _remote_evp_dispatch(intersection_id: str, action_data: dict) -> None:
                    if pipe_conn is not None and getattr(pipe_conn, "closed", False) is not True:
                        try:
                            pipe_conn.send(
                                (
                                    "ai_evp_preempt",
                                    {
                                        "intersection_id": intersection_id,
                                        "action_data": action_data,
                                    },
                                )
                            )
                        except Exception as exc:
                            logging.debug(f"[EngineFactory] Remote EVP dispatch failed: {exc}")

                def _stage_meta_provider(tl_id: str):
                    g_map = getattr(state_extractor, "tl_green_stages", {}) or {}
                    c_map = getattr(state_extractor, "tl_stage_codes", {}) or {}
                    candidates = [str(tl_id), str(tl_id)[3:] if str(tl_id).startswith("tl_") else f"tl_{tl_id}"]
                    g_val = next((g_map[k] for k in candidates if isinstance(g_map, dict) and k in g_map), None)
                    c_val = next((c_map[k] for k in candidates if isinstance(c_map, dict) and k in c_map), None)
                    return g_val, c_val

                EVPBridge.configure_remote_dispatcher(_remote_evp_dispatch)
                EVPBridge.configure_stage_metadata_provider(_stage_meta_provider)
                EVPBridge()
        except Exception as exc_evp:
            logging.debug(f"[EngineFactory] Remote EVPBridge wiring skipped: {exc_evp}")

        # 6. Step Pipeline Collaborators
        step_timer = StepTimer()
        action_masker = PhysicalActionMasker(
            state_extractor=state_extractor,
            action_supervisor=action_supervisor,
        )
        pae_encoder = BatchedPAEEncoder()
        agent_evaluator = AgentEvaluator(
            state_extractor=state_extractor,
            input_preprocessor=input_preprocessor,
            reward_computer=reward_computer,
            action_authorizer=action_authorizer,
            action_supervisor=action_supervisor,
            maturity_manager=maturity_manager,
            locale_manager=locale_manager,
            db_manager=db_manager,
            action_masker=action_masker,
            pae_encoder=pae_encoder,
        )
        stage_transition_manager = StageTransitionManager(
            state_extractor=state_extractor,
            action_supervisor=action_supervisor,
        )
        telemetry_publisher = StepTelemetryPublisher(pipe_conn=pipe_conn)

        def _apply_evp_snapshot(evp_state: dict) -> None:
            from evp.evp_service import EVPService

            EVPService.get_instance().apply_remote_snapshot(evp_state)

        hardware_synchronizer = HardwareTelemetrySynchronizer(
            action_supervisor=action_supervisor,
            state_extractor=state_extractor,
            state_reconciler=state_reconciler,
            telemetry_publisher=telemetry_publisher,
            evp_snapshot_sink=_apply_evp_snapshot,
        )
        try:
            raw_strat_freq = settings.getfloat("GAT_STRATEGIST", "update_frequency_seconds", fallback=5.0)
            strat_freq = float(raw_strat_freq) if isinstance(raw_strat_freq, (int, float)) else 5.0
        except Exception:
            strat_freq = 5.0
        strategic_coordinator = StrategicCoordinator(
            update_frequency_seconds=strat_freq,
            agent_evaluator=agent_evaluator,
            state_extractor=state_extractor,
        )

        step_processor = StepProcessor(
            settings=settings,
            locale_manager=locale_manager,
            step_timer=step_timer,
            agent_evaluator=agent_evaluator,
            stage_transition_manager=stage_transition_manager,
            action_supervisor=action_supervisor,
            online_pae_trainer=online_pae_trainer,
            mfd_processor=mfd_processor,
            hardware_actuator=hardware_actuator,
            telemetry_publisher=telemetry_publisher,
            cycle_manager=cycle_manager,
            episode_reporter=episode_reporter,
            state_reconciler=state_reconciler,
            state_extractor=state_extractor,
            hardware_synchronizer=hardware_synchronizer,
            strategic_coordinator=strategic_coordinator,
            guardian_shadow_trainer=guardian_shadow_trainer,
            maturity_manager=maturity_manager,
        )

        # 7. Scenario Loader (Dedicated Use Case Coordinator)
        scenario_loader = ScenarioLoader(
            step_processor=step_processor,
            agent_manager=agent_manager,
            topology_manager=topology_manager,
            state_extractor=state_extractor,
            maturity_manager=maturity_manager,
            mfd=mfd,
            cycle_manager=cycle_manager,
            mfd_processor=mfd_processor,
        )

        # 8. Trainer Facade & Event Router Handshake
        trainer = Trainer(
            scenario_loader=scenario_loader,
            event_router=None,  # wired immediately below
            pipe_conn=pipe_conn,
            connection_manager=connection_manager,
            action_supervisor=action_supervisor,
            state_reconciler=state_reconciler,
        )

        event_router = EventRouter(
            pipe_conn=pipe_conn,
            trainer_instance=trainer,
            agent_manager=agent_manager,
            step_processor=step_processor,
        )
        trainer.event_router = event_router

        logging.info(f"[EngineFactory] AI Engine wired successfully. GPU: {gpu_info}")
        return trainer
