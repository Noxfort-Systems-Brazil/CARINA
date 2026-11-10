# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
