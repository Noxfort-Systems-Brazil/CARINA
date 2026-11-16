# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import threading
from typing import Any, Dict, Optional, Tuple


class ReportNumberFormatter:
    """
    Responsibility (SRP): Formats numerical values and retrieves distance/time/decimal/thousands
    separator configurations from SettingsManager for ABNT-compliant report rendering.
    """

    _cache_lock = threading.Lock()
    _cached_config: Optional[Dict[str, str]] = None
    _cached_stat: Optional[Tuple[int, int]] = None
    _cached_path: Optional[str] = None

    @classmethod
    def _load_cached_formatting_config(cls) -> Dict[str, str]:
        defaults = {
            "distance_unit": "metros",
            "time_unit": "segundos",
            "decimal_separator": ",",
            "thousands_separator": ".",
        }
        try:
            from utils.settings_manager import SettingsManager
        except Exception:
            return defaults

        is_mocked = hasattr(SettingsManager, "assert_called") or hasattr(
            getattr(SettingsManager, "get_setting", None), "assert_called"
        )

        with cls._cache_lock:
            if not is_mocked and cls._cached_config is not None and cls._cached_path:
                try:
                    st = os.stat(cls._cached_path)
                    stat_sig = (st.st_mtime_ns, st.st_size)
                    if stat_sig == cls._cached_stat:
                        return cls._cached_config
                except OSError:
                    pass

        try:
            sm = SettingsManager()
            cfg_path = getattr(sm, "config_path", None)
            dist_u = (
                str(sm.get_setting("UI", "distance_unit", None) or sm.get_setting("General", "distance_unit", "metros"))
                .strip()
                .lower()
            )
            time_u = (
                str(sm.get_setting("UI", "time_unit", None) or sm.get_setting("General", "time_unit", "segundos"))
                .strip()
                .lower()
            )
            dec_raw = str(
                sm.get_setting("REPORT_FORMATTING", "decimal_separator", None)
                or sm.get_setting("UI", "decimal_separator", ",")
            ).strip()
            dec_sep = "." if dec_raw in (".", "dot", "ponto", "usa", "us") else ","
            thou_raw = str(
                sm.get_setting("REPORT_FORMATTING", "thousands_separator", None)
                or sm.get_setting("UI", "thousands_separator", ".")
            ).strip()
            thou_sep = "," if thou_raw in (",", "comma", "virgula") else "."
            cfg = {
                "distance_unit": dist_u,
                "time_unit": time_u,
                "decimal_separator": dec_sep,
                "thousands_separator": thou_sep,
            }
            if not is_mocked:
                with cls._cache_lock:
                    cls._cached_config = cfg
                    cls._cached_path = cfg_path
                    try:
                        if cfg_path:
                            st = os.stat(cfg_path)
                            cls._cached_stat = (st.st_mtime_ns, st.st_size)
                        else:
                            cls._cached_stat = None
                    except OSError:
                        cls._cached_stat = None
            return cfg
        except Exception:
            return defaults

    @classmethod
    def get_configured_distance_unit(cls) -> str:
        """Retrieves physical distance unit configured in settings.ini / UI."""
        return cls._load_cached_formatting_config()["distance_unit"]

    @classmethod
    def get_configured_time_unit(cls) -> str:
        """Retrieves time unit configured in settings.ini / UI."""
        return cls._load_cached_formatting_config()["time_unit"]

    @classmethod
    def get_configured_decimal_separator(cls) -> str:
        """Retrieves decimal separator (',' or '.') configured in settings.ini / UI."""
        return cls._load_cached_formatting_config()["decimal_separator"]

    @classmethod
    def get_configured_thousands_separator(cls) -> str:
        """Retrieves thousands separator ('.' or ',') configured in settings.ini / UI."""
        return cls._load_cached_formatting_config()["thousands_separator"]

    @classmethod
    def format_number(cls, val: Any, decimal_places: int = 1) -> str:
        """Formats float or int value with configured thousands and decimal separators."""
        if val is None or val == "":
            return "0"
        try:
            num = float(val)
            cfg = cls._load_cached_formatting_config()
            dec_sep = cfg["decimal_separator"]
            thou_sep = cfg["thousands_separator"]
            formatted = f"{num:,.{decimal_places}f}"
            if dec_sep == "." and thou_sep == ",":
                return formatted
            return formatted.replace(",", "\x00").replace(".", dec_sep).replace("\x00", thou_sep)
        except Exception:
            return str(val)
