# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any


class ReportNumberFormatter:
    """
    Responsibility (SRP): Formats numerical values and retrieves distance/time/decimal/thousands
    separator configurations from SettingsManager for ABNT-compliant report rendering.
    """

    @staticmethod
    def get_configured_distance_unit() -> str:
        """Retrieves physical distance unit configured in settings.ini / UI."""
        try:
            from utils.settings_manager import SettingsManager

            sm = SettingsManager()
            unit = sm.get_setting("UI", "distance_unit", None) or sm.get_setting("General", "distance_unit", "metros")
            return str(unit).strip().lower()
        except Exception:
            return "metros"

    @staticmethod
    def get_configured_time_unit() -> str:
        """Retrieves time unit configured in settings.ini / UI."""
        try:
            from utils.settings_manager import SettingsManager

            sm = SettingsManager()
            unit = sm.get_setting("UI", "time_unit", None) or sm.get_setting("General", "time_unit", "segundos")
            return str(unit).strip().lower()
        except Exception:
            return "segundos"

    @staticmethod
    def get_configured_decimal_separator() -> str:
        """Retrieves decimal separator (',' or '.') configured in settings.ini / UI."""
        try:
            from utils.settings_manager import SettingsManager

            sm = SettingsManager()
            sep = sm.get_setting("REPORT_FORMATTING", "decimal_separator", None) or sm.get_setting(
                "UI", "decimal_separator", ","
            )
            sep = str(sep).strip()
            if sep in (".", "dot", "ponto", "usa", "us"):
                return "."
            return ","
        except Exception:
            return ","

    @staticmethod
    def get_configured_thousands_separator() -> str:
        """Retrieves thousands separator ('.' or ',') configured in settings.ini / UI."""
        try:
            from utils.settings_manager import SettingsManager

            sm = SettingsManager()
            sep = sm.get_setting("REPORT_FORMATTING", "thousands_separator", None) or sm.get_setting(
                "UI", "thousands_separator", "."
            )
            sep = str(sep).strip()
            if sep in (",", "comma", "virgula"):
                return ","
            return "."
        except Exception:
            return "."

    @classmethod
    def format_number(cls, val: Any, decimal_places: int = 1) -> str:
        """Formats float or int value with configured thousands and decimal separators."""
        if val is None or val == "":
            return "0"
        try:
            num = float(val)
            dec_sep = cls.get_configured_decimal_separator()
            if dec_sep == ".":
                return f"{num:,.{decimal_places}f}"
            else:
                formatted = f"{num:,.{decimal_places}f}"
                return formatted.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        except Exception:
            return str(val)
