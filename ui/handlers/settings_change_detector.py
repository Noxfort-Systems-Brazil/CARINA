# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unsaved Settings Changes Detector (SRP / Clean Architecture).
Performs polymorphic comparisons (boolean, numeric, and textual) between saved and current state.
"""

from typing import Any, List, Optional


class SettingsChangeDetector:
    """Checks whether there are pending modifications across settings cards."""

    @staticmethod
    def has_unsaved_changes(
        all_cards: List[Any],
        hardware_handler: Optional[Any],
        settings_handler: Any,
        evp_handler: Optional[Any] = None,
    ) -> bool:
        """Determines whether any card or control differs from persisted state."""
        for card in all_cards:
            if hasattr(card, "has_unsaved_changes") and callable(card.has_unsaved_changes):
                if card.has_unsaved_changes():
                    return True

        if hardware_handler and hasattr(hardware_handler, "has_unsaved_changes") and callable(hardware_handler.has_unsaved_changes):
            if hardware_handler.has_unsaved_changes():
                return True

        if evp_handler and hasattr(evp_handler, "has_unsaved_changes") and callable(evp_handler.has_unsaved_changes):
            if evp_handler.has_unsaved_changes():
                return True

        saved = settings_handler.get_current_settings()
        current = {}
        for card in all_cards:
            if hasattr(card, "get_values"):
                current.update(card.get_values())

        for key, curr_val in current.items():
            if key not in saved:
                continue
            saved_val = saved[key]

            # 1. Boolean comparison
            saved_str_lower = str(saved_val).strip().lower() if saved_val is not None else ""
            curr_str_lower = str(curr_val).strip().lower() if curr_val is not None else ""
            if (
                isinstance(saved_val, bool)
                or isinstance(curr_val, bool)
                or saved_str_lower in ("true", "false")
                or curr_str_lower in ("true", "false")
            ):
                s_bool = saved_val if isinstance(saved_val, bool) else saved_str_lower in ("true", "1", "yes", "on")
                c_bool = curr_val if isinstance(curr_val, bool) else curr_str_lower in ("true", "1", "yes", "on")
                if s_bool != c_bool:
                    return True
                continue

            # 2. Numeric comparison (float / int)
            try:
                s_float = float(saved_val)
                c_float = float(curr_val)
                if abs(s_float - c_float) > 1e-6:
                    return True
                continue
            except (ValueError, TypeError):
                pass

            # 3. String comparison
            s_str = str(saved_val or "").strip()
            c_str = str(curr_val or "").strip()
            if s_str != c_str:
                return True

        return False
