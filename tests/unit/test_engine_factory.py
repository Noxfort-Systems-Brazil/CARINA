# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import configparser
import pytest

from engine.engine_factory import EngineFactory
from engine.scenario_loader import ScenarioLoader
from engine.trainer import Trainer


def test_engine_factory_create_trainer(tmp_path):
    """Verifies that EngineFactory constructs and wires all engine collaborators."""
    settings = configparser.ConfigParser()
    settings.add_section("AI_TRAINING")
    settings.set("AI_TRAINING", "sequence_length", "4")
    settings.set("AI_TRAINING", "episode_max_steps", "100")
    settings.add_section("PAE")
    settings.set("PAE", "update_frequency_seconds", "5")
    settings.set("PAE", "learning_rate", "0.0005")

    mock_pipe = MagicMock()
    log_dir = str(tmp_path / "logs")

    trainer = EngineFactory.create_trainer(
        settings=settings,
        log_dir=log_dir,
        gpu_info="Mock GPU",
        pipe_conn=mock_pipe,
    )

    assert isinstance(trainer, Trainer)
    assert isinstance(trainer.scenario_loader, ScenarioLoader)
    assert trainer.event_router is not None
    assert trainer.pipe_conn is mock_pipe
