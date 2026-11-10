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
from maturity.maturity_manager import MaturityManager
from drivers.hardware_stage_actuator import HardwareStageActuator
from engine.action_supervisor import ActionSupervisor
from engine.agent_evaluator import AgentEvaluator
from engine.event_router import EventRouter
from engine.input_preprocessor import InputPreprocessor
from engine.online_pae_trainer import OnlinePAETrainer
from engine.reward_computer import RewardComputer
from engine.scenario_loader import ScenarioLoader
from engine.state_extractor import StateExtractor
from engine.step_processor import StepProcessor
from engine.step_telemetry_publisher import StepTelemetryPublisher
from engine.step_timer import StepTimer
from engine.trainer import Trainer
from manager.agent_manager import AgentManager
from manager.cycle_manager import CycleManager
from manager.stage_transition_manager import StageTransitionManager
from manager.agent_population_loader import AgentPopulationLoader as TopologyManager
from mfd.mfd import MacroscopicFundamentalDiagram
from mfd.mfd_processor import MFDProcessor
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
        cycle_manager = CycleManager(maturity_manager=maturity_manager, pipe_conn=pipe_conn, settings=settings)
        mfd = MacroscopicFundamentalDiagram()
        mfd_processor = MFDProcessor(mfd=mfd, state_extractor=state_extractor)
        episode_reporter = EpisodeReporter(locale_manager=locale_manager, maturity_manager=maturity_manager)

        # 5. FENIX State Reconciler
        try:
            from fenix.state_reconciler import StateReconciler

            state_reconciler = StateReconciler()
        except Exception:
            state_reconciler = None

        # 6. Step Pipeline Collaborators
        step_timer = StepTimer()
        agent_evaluator = AgentEvaluator(
            state_extractor=state_extractor,
            input_preprocessor=input_preprocessor,
            reward_computer=reward_computer,
            action_authorizer=action_authorizer,
            action_supervisor=action_supervisor,
            maturity_manager=maturity_manager,
            locale_manager=locale_manager,
            db_manager=db_manager,
        )
        stage_transition_manager = StageTransitionManager(
            state_extractor=state_extractor,
            action_supervisor=action_supervisor,
        )
        telemetry_publisher = StepTelemetryPublisher(pipe_conn=pipe_conn)

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
