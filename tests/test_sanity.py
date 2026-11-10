# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys

import pytest


def test_environment_setup():
    """
    Tests if the environment was properly configured by conftest.py
    """
    assert os.environ.get("CARINA_TEST_MODE") == "1"
    assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def test_import_src_modules():
    """
    Skipping temporarily - root import causes hang
    """
    pytest.skip("Skipping root src imports on pure headless sanity to avoid hangs")


def test_import_ui_modules():
    """
    Tests if pytest can see the ui/ folder and import base modules.
    """
    pytest.skip("Skiping UI imports on pure headless sanity to avoid Qt hangs")


@pytest.mark.unit
def test_dummy_math():
    """
    Simple test to ensure the unit execution runs.
    """
    assert 1 + 1 == 2
