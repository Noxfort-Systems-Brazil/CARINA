# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch

import pytest

from mfd.mfd_processor import MFDProcessor


def test_mfd_processor_no_mfd():
    processor = MFDProcessor(mfd=None, state_extractor=None)
    res = processor.process_step(edges_data={}, sim_time=1.0, agents_keys=[], step_counter=1, episode_steps=100)
    assert res is None


def test_mfd_processor_no_edges():
    mfd = MagicMock()
    processor = MFDProcessor(mfd=mfd, state_extractor=None)
    res = processor.process_step(edges_data={}, sim_time=1.0, agents_keys=[], step_counter=1, episode_steps=100)
    assert res is None


def test_mfd_processor_compute_step():
    mfd = MagicMock()
    mfd_snapshot = MagicMock()
    mfd_snapshot.to_dict.return_value = {"efficiency": 0.9}
    mfd.compute_step.return_value = mfd_snapshot
    mfd._edge_lengths = {"edge_1": 150.0}

    state_extractor = MagicMock()
    state_extractor.tl_incoming_edges = {"tl_1": ["edge_1"]}

    processor = MFDProcessor(mfd=mfd, state_extractor=state_extractor)

    edges_data = {"edge_1": {"density": 0.05, "mean_speed": 10.0, "occupancy": 0.1, "queue_length": 5}}

    res = processor.process_step(
        edges_data=edges_data, sim_time=1.0, agents_keys=["tl_1"], step_counter=1, episode_steps=100
    )

    assert res == {"efficiency": 0.9}
    mfd.compute_step.assert_called_once()
