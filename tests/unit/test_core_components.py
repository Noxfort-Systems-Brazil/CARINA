# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys

import pytest


def test_enums_maturity():
    """
    Tests if we can load and use the core Enums (Maturity)
    """
    try:
        from src.core.enums import Maturity

        assert Maturity.CHILD.name == "CHILD"
        assert Maturity.ADULT.name == "ADULT"
    except ImportError as e:
        pytest.fail(f"Failed to load core enums: {e}")


def test_ai_process_function_exists():
    """
    Tests if the main AI entry port (HFT) exists
    (without invoking it to avoid setting up tensors).
    """
    try:
        from src.main import run_ai_process

        assert callable(run_ai_process), "run_ai_process must be callable"
    except ImportError as e:
        pytest.fail(f"Failed to load main.py: {e}")


@pytest.mark.unit
def test_locale_backend():
    """
    Ensures that the locale manager can be initialized without crashing.
    """
    try:
        from src.utils.locale_manager_backend import LocaleManagerBackend

        lm = LocaleManagerBackend()
        # The default should be pt_BR or en_US, testing if it's not empty
        assert lm.current_lang_data is not None
        assert isinstance(lm.get_string("dummy.key", fallback="fallback_value"), str)
    except Exception as e:
        pytest.fail(f"Failure in Locales Manager: {e}")
