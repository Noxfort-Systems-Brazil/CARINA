# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_launcher_env_setup.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import sys
from unittest.mock import patch

import pytest

from launcher.env_setup import setup_environment


def test_setup_environment_standard_mode():
    """Tests setup_environment in standard (unfrozen) python runtime."""
    with patch.object(sys, "frozen", False, create=True):
        project_root, bundle_root, is_frozen = setup_environment()
        assert is_frozen is False
        assert os.path.exists(project_root)
        assert project_root == bundle_root

        # Assert environment variables set
        assert os.environ.get("OMP_NUM_THREADS") == "1"
        assert os.environ.get("MKL_NUM_THREADS") == "1"
        assert os.environ.get("OPENBLAS_NUM_THREADS") == "1"
        assert os.environ.get("TF_ENABLE_ONEDNN_OPTS") == "0"

        # Assert required subdirectories in sys.path
        for sub in ["src", "proto", "ui"]:
            expected_path = os.path.join(bundle_root, sub)
            assert expected_path in sys.path


def test_setup_environment_frozen_mode():
    """Tests setup_environment in PyInstaller frozen execution mode."""
    mock_bundle = "/tmp/mock_bundle_carina"
    mock_exec = "/opt/carina/carina"

    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "_MEIPASS", mock_bundle, create=True),
        patch.object(sys, "executable", mock_exec),
    ):

        project_root, bundle_root, is_frozen = setup_environment()
        assert is_frozen is True
        assert project_root == "/opt/carina"
        assert bundle_root == mock_bundle
        assert os.path.join(mock_bundle, "src") in sys.path
        assert os.path.join(mock_bundle, "proto") in sys.path
        assert os.path.join(mock_bundle, "ui") in sys.path
