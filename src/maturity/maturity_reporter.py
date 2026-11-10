# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING

from core.enums import Maturity

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class MaturityReporter:
    """The "Spokesperson" of the Flight School, specialist in generating log reports."""

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        self.locale_manager = locale_manager

    def report_promotion(self, agent_id: str, new_phase: Maturity, details: dict):
        """Formats and logs a successful promotion message."""
        lm = self.locale_manager

        is_graduation = new_phase == Maturity.ADULT
        icon = "🎓" if is_graduation else "✅"

        title_key = (
            "maturity_reporter.promotion.title_graduated"
            if is_graduation
            else "maturity_reporter.promotion.title_promoted"
        )
        title = lm.get_string(title_key)

        # --- CHANGE 1: Use a key that contains the entire header structure ---
        header = lm.get_string("maturity_reporter.promotion.header", icon=icon, title=title, agent_id=agent_id)

        phase_map = {Maturity.TEEN: "teen", Maturity.ADULT: "adult"}
        phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(new_phase, 'child')}")

        log_message = f"\n{header}\n"
        log_message += f"   L- {lm.get_string('maturity_manager.new_phase_message', phase_name=phase_name)}.\n"
        log_message += f"   L- {lm.get_string('maturity_manager.criteria_met_header')}"

        for criterion, value in details.items():
            if isinstance(value, dict):
                val_str = value.get("msg", str(value))
            else:
                val_str = str(value)
            log_message += f"\n      - ✅ {criterion}: {val_str}"
        logging.info(log_message)

    def report_rejection(self, agent_id: str, current_phase: Maturity, target_phase: Maturity, details: dict):
        """Formats and logs a detailed "report card" for a failed promotion attempt."""
        lm = self.locale_manager

        title = lm.get_string("maturity_reporter.rejection.title")

        phase_map = {Maturity.CHILD: "child", Maturity.TEEN: "teen", Maturity.ADULT: "adult"}
        current_phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(current_phase, 'child')}")
        target_phase_name = lm.get_string(f"maturity_manager.phase_{phase_map.get(target_phase, 'teen')}")

        # --- CHANGE 2: Use a key that contains the entire header structure ---
        header = lm.get_string(
            "maturity_reporter.rejection.header", title=title, agent_id=agent_id, current_phase_name=current_phase_name
        )

        log_message = f"\n{header} "
        log_message += lm.get_string("maturity_manager.promotion_not_met_message", target_phase_name=target_phase_name)
        log_message += f"\n   L- {lm.get_string('maturity_manager.criteria_status_header')}"

        for criterion, data in details.items():
            if isinstance(data, dict):
                icon = "✅" if data.get("ok", False) else "❌"
                msg = data.get("msg", str(data))
            else:
                icon = "ℹ️"
                msg = str(data)
            log_message += f"\n      - {icon} {criterion}: {msg}"
        logging.info(log_message)

    def build_promotion_details(
        self,
        episodes_in_phase: int,
        required_episodes: int,
        agent_entropy: float,
        entropy_threshold: float,
        reason: str,
        mode_str: str = "MANUAL",
    ) -> dict:
        lm = self.locale_manager
        mfd_label = lm.get_string("maturity_manager.criterion_mfd", default="MFD Efficiency")
        return {
            "Modo DA SILVA": mode_str,
            lm.get_string("maturity_manager.criterion_time"): lm.get_string(
                "maturity_manager.time_details",
                episodes_in_phase=episodes_in_phase,
                required_episodes=required_episodes,
            ),
            lm.get_string("maturity_manager.criterion_confidence"): lm.get_string(
                "maturity_manager.confidence_details",
                agent_entropy=agent_entropy,
                entropy_threshold=entropy_threshold,
            ),
            mfd_label: reason,
        }

    def build_rejection_details(
        self,
        episodes_in_phase: int,
        required_episodes: int,
        agent_entropy: float,
        entropy_threshold: float,
        confidence_ok: bool,
        is_promoted: bool,
        reason: str,
        mode_str: str = "MANUAL",
    ) -> dict:
        lm = self.locale_manager
        return {
            "Modo DA SILVA": {
                "ok": True,
                "msg": mode_str,
            },
            lm.get_string("maturity_manager.criterion_time"): {
                "ok": episodes_in_phase >= required_episodes,
                "msg": lm.get_string(
                    "maturity_manager.time_details",
                    episodes_in_phase=episodes_in_phase,
                    required_episodes=required_episodes,
                ),
            },
            lm.get_string("maturity_manager.criterion_confidence"): {
                "ok": confidence_ok,
                "msg": lm.get_string(
                    "maturity_manager.confidence_details",
                    agent_entropy=agent_entropy,
                    entropy_threshold=entropy_threshold,
                ),
            },
            lm.get_string("maturity_manager.criterion_mfd", default="MFD Efficiency"): {
                "ok": is_promoted,
                "msg": reason,
            },
        }
