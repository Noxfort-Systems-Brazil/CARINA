# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Any, Dict, Optional

from maturity.maturity_repository_port import MaturityRepositoryPort


class MaturityStateRepository(MaturityRepositoryPort):
    """Infrastructure repository responsible for saving and loading MaturityManager state on disk."""

    @staticmethod
    def save(filepath: str, state: Dict[str, Any], locale_manager: Any = None) -> bool:
        """Saves maturity state dictionary to a JSON file."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
            if locale_manager:
                logging.info(locale_manager.get_string("maturity_manager.save.success", path=filepath))
            return True
        except IOError as e:
            if locale_manager:
                logging.error(locale_manager.get_string("maturity_manager.save.error", error=e))
            else:
                logging.error(f"[MaturityStateRepository] Error saving state to {filepath}: {e}")
            return False

    @staticmethod
    def load(filepath: str, locale_manager: Any = None) -> Optional[dict]:
        """Loads maturity state dictionary from a JSON file."""
        if not os.path.exists(filepath):
            if locale_manager:
                logging.warning(locale_manager.get_string("maturity_manager.load.not_found", path=filepath))
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)
            if locale_manager:
                logging.info(locale_manager.get_string("maturity_manager.load.success", path=filepath))
            return state
        except (json.JSONDecodeError, KeyError, IOError) as e:
            if locale_manager:
                logging.error(locale_manager.get_string("maturity_manager.load.error", error=e), exc_info=True)
            else:
                logging.error(f"[MaturityStateRepository] Error loading state from {filepath}: {e}", exc_info=True)
            return None
