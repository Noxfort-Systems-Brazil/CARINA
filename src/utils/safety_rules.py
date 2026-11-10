# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os


class SafetyRules:
    _rules = None

    @classmethod
    def get_rules(cls, locale_manager=None) -> dict:
        def get_str(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        if cls._rules is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(base_dir, "config", "rules", "safety_rules.json"),
                os.path.join(base_dir, "config", "safety_rules.json"),
            ]
            rules_path = None
            for p in candidates:
                if os.path.exists(p):
                    rules_path = p
                    break
            if rules_path is None:
                rules_path = candidates[0]

            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    cls._rules = json.load(f)
                logging.info(
                    get_str(
                        "safety_rules.loaded", default="[SafetyRules] Safety rules loaded from {path}", path=rules_path
                    )
                )
            except Exception as e:
                logging.warning(
                    get_str(
                        "safety_rules.load_failed",
                        default="[SafetyRules] Failed to load safety_rules.json ({error}). Using engineering default fallback.",
                        error=e,
                    )
                , exc_info=True)
                cls._rules = {
                    "green_time_seconds": 10.0,
                    "max_green_time_seconds": 60.0,
                    "yellow_time_seconds": 4.0,
                    "all_red_time_seconds": 3.0,
                    "red_time_seconds": 10.0,
                }
        return cls._rules

    @classmethod
    def get_green(cls) -> float:
        return float(cls.get_rules().get("green_time_seconds", 10.0))

    @classmethod
    def get_max_green(cls) -> float:
        return float(cls.get_rules().get("max_green_time_seconds", 60.0))

    @classmethod
    def get_yellow(cls) -> float:
        return float(cls.get_rules().get("yellow_time_seconds", 4.0))

    @classmethod
    def get_all_red(cls) -> float:
        return float(cls.get_rules().get("all_red_time_seconds", 3.0))

    @classmethod
    def get_red(cls) -> float:
        return float(cls.get_rules().get("red_time_seconds", 10.0))
