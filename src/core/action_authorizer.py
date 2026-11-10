# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
ActionAuthorizer: Gatekeeper module enforcing maturity stage action permissions.
Restricts CHILD to observation, enforces Synapse peak gating on TEEN, and authorizes ADULT.
"""

from datetime import datetime
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from core.enums import Maturity

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

logger = logging.getLogger(__name__)


class ActionAuthorizer:
    """
    Authorizes agent actuation based on maturity level and real-world time-of-day peak profiles.
    """

    def __init__(
        self,
        settings: Any,
        locale_manager: Optional["LocaleManagerBackend"] = None,
        traffic_profiles: Optional[Dict[int, Dict[str, str]]] = None,
    ):
        """
        Initializes the authorizer with settings, locale manager, and traffic profiles.
        """
        self.settings = settings
        self.locale_manager = locale_manager

        if traffic_profiles:
            self.traffic_profiles = traffic_profiles
        else:
            self.traffic_profiles = self._build_classical_urban_peak_fallback()

    def set_traffic_profiles(self, profiles: Dict[Any, Dict[str, str]]) -> None:
        """Dynamically injects traffic profiles parsed from Synapse or configuration."""
        normalized: Dict[int, Dict[str, str]] = {}
        for day, hours in profiles.items():
            try:
                day_idx = int(day)
                normalized[day_idx] = {str(h): str(lvl).lower() for h, lvl in hours.items()}
            except (ValueError, TypeError):
                continue
        if normalized:
            self.traffic_profiles = normalized
            logger.info("[ActionAuthorizer] Updated traffic profiles from external schedule.")

    def load_peak_schedule_json(self, schedule_json: Union[str, bytes]) -> bool:
        """Parses and applies a peak schedule JSON string received over HFT."""
        if not schedule_json:
            return False
        try:
            if isinstance(schedule_json, bytes):
                schedule_json = schedule_json.decode("utf-8")
            data = json.loads(schedule_json)
            if isinstance(data, dict):
                self.set_traffic_profiles(data)
                return True
        except Exception as e:
            logger.error(f"[ActionAuthorizer] Error loading peak schedule JSON: {e}", exc_info=True)
        return False

    def is_action_authorized(
        self,
        agent_id: str,
        maturity: Maturity,
        sim_time: float,
        raw_timestamp: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Validates if an agent is authorized to act on physical traffic lights.

        Args:
            agent_id: Identifier of the junction agent.
            maturity: Current maturity phase enum.
            sim_time: Relative elapsed simulation time in seconds.
            raw_timestamp: Epoch timestamp in seconds from the HFT frame.

        Returns:
            Tuple of (is_authorized, reason_string).
        """
        lm = self.locale_manager
        reason_child = (
            lm.get_string("action_authorizer.reason.child", fallback="Nível Criança: Apenas observação.")
            if lm else "Nível Criança: Apenas observação."
        )
        reason_adult = (
            lm.get_string("action_authorizer.reason.adult", fallback="Nível Adulto: Autorizado.")
            if lm else "Nível Adulto: Autorizado."
        )
        reason_teen_peak = (
            lm.get_string("action_authorizer.reason.teen_peak", fallback="Nível Adolescente: Proibido em horário de pico.")
            if lm else "Nível Adolescente: Proibido em horário de pico."
        )
        reason_teen_offpeak = (
            lm.get_string("action_authorizer.reason.teen_offpeak", fallback="Nível Adolescente: Autorizado fora de pico.")
            if lm else "Nível Adolescente: Autorizado fora de pico."
        )
        reason_unknown = (
            lm.get_string("action_authorizer.reason.unknown", fallback="Maturidade desconhecida.")
            if lm else "Maturidade desconhecida."
        )

        if maturity == Maturity.CHILD:
            return False, reason_child

        if maturity == Maturity.ADULT:
            return True, reason_adult

        if maturity == Maturity.TEEN:
            # Resolve real calendar day and hour from raw frame timestamp if available
            if raw_timestamp is not None and raw_timestamp > 0:
                try:
                    dt = datetime.fromtimestamp(raw_timestamp)
                except (ValueError, OSError, OverflowError):
                    dt = datetime.now()
            elif sim_time > 1e8:  # Absolute epoch passed in sim_time
                try:
                    dt = datetime.fromtimestamp(sim_time)
                except (ValueError, OSError, OverflowError):
                    dt = datetime.now()
            else:
                # Relative elapsed seconds: assumes starting Monday 00:00 as historical fallback
                day_idx = int(sim_time // 86400) % 7
                hour_of_day = str(int((sim_time % 86400) // 3600))
                profile_for_day = self.traffic_profiles.get(day_idx, {})
                traffic_level = profile_for_day.get(hour_of_day, "low")
                if traffic_level == "peak":
                    return False, reason_teen_peak
                return True, reason_teen_offpeak

            day_index = dt.weekday()
            hour_of_day = str(dt.hour)

            profile_for_day = self.traffic_profiles.get(day_index, {})
            traffic_level = profile_for_day.get(hour_of_day, "low")

            if traffic_level == "peak":
                return False, reason_teen_peak

            return True, reason_teen_offpeak

        return False, reason_unknown

    @staticmethod
    def _build_classical_urban_peak_fallback() -> Dict[int, Dict[str, str]]:
        """
        Builds standard municipal traffic engineering peak profile:
        - Monday to Friday (0..4): Morning peak (06:00-09:00), Evening peak (17:00-20:00).
        - Saturday and Sunday (5, 6): Off-peak (all low).
        """
        profiles: Dict[int, Dict[str, str]] = {}
        for day in range(7):
            profiles[day] = {}
            for hour in range(24):
                if day < 5 and hour in (6, 7, 8, 17, 18, 19):
                    profiles[day][str(hour)] = "peak"
                else:
                    profiles[day][str(hour)] = "low"
        return profiles
