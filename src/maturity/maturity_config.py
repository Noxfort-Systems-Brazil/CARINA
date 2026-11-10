# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MaturityConfig:
    """Configuration Value Object for agent maturity life-cycle policies."""

    baseline_performance: float = -10000.0
    performance_margin_percent: float = 5.0
    child_phase_duration: int = 5
    teen_phase_min_duration: int = 50
    rewards_window_size: int = 10
    child_promotion_max_entropy: Optional[float] = None
    auto_pacing_enabled: bool = True
    auto_performance_margin_enabled: bool = True

    @property
    def performance_margin(self) -> float:
        return 1.0 + (self.performance_margin_percent / 100.0)

    @property
    def baseline_target(self) -> float:
        return self.baseline_performance * self.performance_margin

    @property
    def is_automatic_mode(self) -> bool:
        return self.auto_pacing_enabled or self.auto_performance_margin_enabled

    def set_phase_durations(self, child_episodes: int, teen_episodes: int) -> None:
        self.child_phase_duration = max(1, int(child_episodes))
        self.teen_phase_min_duration = max(1, int(teen_episodes))

    def set_performance_margin(self, margin_percent: float) -> None:
        self.performance_margin_percent = float(margin_percent)

    @classmethod
    def from_settings(cls, settings: Any, baseline: Optional[dict] = None) -> "MaturityConfig":
        """Builds a MaturityConfig instance parsing ConfigParser or dict configurations."""
        if baseline and "mean_reward" in baseline:
            base_perf = float(baseline["mean_reward"])
        else:
            base_perf = -10000.0
            if hasattr(settings, "getfloat"):
                try:
                    base_perf = settings.getfloat("MATURITY", "baseline_reward", fallback=-10000.0)
                except (ValueError, TypeError, configparser.Error):
                    base_perf = -10000.0
            elif isinstance(settings, dict):
                mat_section = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
                base_perf = float(settings.get("baseline_reward", mat_section.get("baseline_reward", -10000.0)))

        def _get_float(key: str, fallback: float) -> float:
            if hasattr(settings, "getfloat"):
                try:
                    return settings.getfloat("MATURITY", key, fallback=fallback)
                except (ValueError, TypeError, configparser.Error):
                    return fallback
            elif isinstance(settings, dict):
                mat_sec = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
                val = settings.get(key, mat_sec.get(key, fallback))
                return float(val) if val is not None else fallback
            return fallback

        def _get_int(key: str, fallback: int) -> int:
            if hasattr(settings, "getint"):
                try:
                    return settings.getint("MATURITY", key, fallback=fallback)
                except (ValueError, TypeError, configparser.Error):
                    return fallback
            elif isinstance(settings, dict):
                mat_sec = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
                val = settings.get(key, mat_sec.get(key, fallback))
                return int(val) if val is not None else fallback
            return fallback

        margin_percent = _get_float("performance_margin_percent", 5.0)
        child_eps = _get_int("child_phase_episodes", 5)
        teen_eps = _get_int("teen_phase_min_episodes", 50)
        win_size = _get_int("performance_check_window", 10)

        child_max_ent = None
        if hasattr(settings, "getfloat"):
            try:
                child_max_ent = settings.getfloat("MATURITY", "child_promotion_max_entropy")
            except (ValueError, TypeError, configparser.Error):
                child_max_ent = None
        elif isinstance(settings, dict):
            mat_sec = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
            val = settings.get("child_promotion_max_entropy", mat_sec.get("child_promotion_max_entropy"))
            if val is not None:
                try:
                    child_max_ent = float(val)
                except (ValueError, TypeError):
                    child_max_ent = None

        auto_pacing = True
        if hasattr(settings, "getboolean"):
            try:
                auto_pacing = settings.getboolean("MATURITY", "auto_pacing_enabled", fallback=True)
            except (ValueError, TypeError, configparser.Error):
                auto_pacing = True
        elif isinstance(settings, dict):
            mat_sec = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
            val = settings.get("auto_pacing_enabled", mat_sec.get("auto_pacing_enabled", True))
            auto_pacing = str(val).lower() in ("true", "1", "yes")

        auto_margin = True
        if hasattr(settings, "getboolean"):
            try:
                auto_margin = settings.getboolean("MATURITY", "auto_performance_margin_enabled", fallback=True)
            except (ValueError, TypeError, configparser.Error):
                auto_margin = True
        elif isinstance(settings, dict):
            mat_sec = settings.get("MATURITY", {}) if isinstance(settings.get("MATURITY"), dict) else {}
            val = settings.get("auto_performance_margin_enabled", mat_sec.get("auto_performance_margin_enabled", True))
            auto_margin = str(val).lower() in ("true", "1", "yes")

        return cls(
            baseline_performance=base_perf,
            performance_margin_percent=margin_percent,
            child_phase_duration=child_eps,
            teen_phase_min_duration=teen_eps,
            rewards_window_size=win_size,
            child_promotion_max_entropy=child_max_ent,
            auto_pacing_enabled=auto_pacing,
            auto_performance_margin_enabled=auto_margin,
        )
