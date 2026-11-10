# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Tracks real calendar weekly coverage across 168 discrete time slots (7 days x 24 hours).
Ensures atomic persistence for crash and pause/resume tolerance in DA SILVA maturation.
"""

from datetime import datetime
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class WeeklyCoverageTracker:
    """
    Manages observation coverage across all 168 real-world hourly time slots of the week.
    Provides persistence on disk to support session pause and resume without progress loss.
    """

    TOTAL_SLOTS = 168  # 7 days * 24 hours

    def __init__(self, cache_dir: str, phase_name: str = "CHILD"):
        """
        Initializes the weekly coverage tracker.

        Args:
            cache_dir: Directory where JSON coverage state files are stored.
            phase_name: Active maturation phase ('CHILD' or 'TEEN').
        """
        self.cache_dir = cache_dir
        self.phase_name = phase_name.upper()
        self.cache_file = os.path.join(self.cache_dir, f"weekly_coverage_{self.phase_name.lower()}.json")

        # Matrix: slots[day_str][hour_str] = {"steps": int, "reward_sum": float, "samples": int}
        self.slots: Dict[str, Dict[str, Dict[str, Any]]] = self._initialize_empty_matrix()
        self.total_recorded_steps = 0
        self.start_timestamp: Optional[float] = None
        self.last_timestamp: Optional[float] = None

        os.makedirs(self.cache_dir, exist_ok=True)
        self.load_from_disk()

    def record_step(self, raw_timestamp: float, reward: float = 0.0) -> Tuple[int, int]:
        """
        Records a telemetry step into its corresponding calendar time slot.

        Args:
            raw_timestamp: Epoch timestamp in seconds from the HFT frame.
            reward: Scalar reward observed in this step.

        Returns:
            Tuple containing (day_of_week, hour_of_day).
        """
        if raw_timestamp <= 0:
            dt = datetime.now()
        else:
            try:
                dt = datetime.fromtimestamp(raw_timestamp)
            except (ValueError, OSError, OverflowError):
                dt = datetime.now()

        day_idx = dt.weekday()  # 0 = Monday, 6 = Sunday
        hour_idx = dt.hour      # 0 .. 23

        day_key = str(day_idx)
        hour_key = str(hour_idx)

        slot = self.slots[day_key][hour_key]
        slot["steps"] += 1
        slot["reward_sum"] += float(reward)
        slot["samples"] += 1

        self.total_recorded_steps += 1
        if self.start_timestamp is None:
            self.start_timestamp = raw_timestamp
        self.last_timestamp = raw_timestamp

        return day_idx, hour_idx

    def get_covered_slots_count(self, min_steps_per_slot: int = 50) -> int:
        """
        Counts the number of discrete hourly slots meeting the minimum observation step threshold.
        """
        covered = 0
        for day in range(7):
            day_key = str(day)
            for hour in range(24):
                hour_key = str(hour)
                if self.slots[day_key][hour_key]["steps"] >= min_steps_per_slot:
                    covered += 1
        return covered

    def is_week_completed(
        self, min_steps_per_slot: int = 50, required_coverage_pct: float = 0.95
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Evaluates whether the 1-week observation coverage criterion has been satisfied.

        Args:
            min_steps_per_slot: Minimum steps required per hourly slot.
            required_coverage_pct: Fraction of the 168 slots that must be covered (default: 0.95).

        Returns:
            Tuple of (is_completed, covered_pct, statistics_dict).
        """
        covered_count = self.get_covered_slots_count(min_steps_per_slot)
        covered_pct = covered_count / float(self.TOTAL_SLOTS)
        is_completed = covered_pct >= required_coverage_pct

        stats = {
            "phase": self.phase_name,
            "covered_slots": covered_count,
            "total_slots": self.TOTAL_SLOTS,
            "coverage_pct": covered_pct,
            "total_steps": self.total_recorded_steps,
            "start_timestamp": self.start_timestamp,
            "last_timestamp": self.last_timestamp,
        }

        return is_completed, covered_pct, stats

    def save_to_disk(self) -> bool:
        """Persists the coverage state atomically to disk."""
        payload = {
            "phase": self.phase_name,
            "total_recorded_steps": self.total_recorded_steps,
            "start_timestamp": self.start_timestamp,
            "last_timestamp": self.last_timestamp,
            "slots": self.slots,
        }
        temp_file = f"{self.cache_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(temp_file, self.cache_file)
            return True
        except Exception as e:
            logger.error(f"[WeeklyCoverageTracker] Failed to save coverage to {self.cache_file}: {e}", exc_info=True)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            return False

    def load_from_disk(self) -> bool:
        """Restores coverage state from disk if present."""
        if not os.path.exists(self.cache_file):
            return False

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.total_recorded_steps = data.get("total_recorded_steps", 0)
            self.start_timestamp = data.get("start_timestamp")
            self.last_timestamp = data.get("last_timestamp")
            loaded_slots = data.get("slots", {})

            for day_key, hours in loaded_slots.items():
                if day_key in self.slots:
                    for hour_key, slot_data in hours.items():
                        if hour_key in self.slots[day_key]:
                            self.slots[day_key][hour_key] = slot_data

            logger.info(
                f"[WeeklyCoverageTracker] Restored state for {self.phase_name}: "
                f"{self.total_recorded_steps} steps, "
                f"{self.get_covered_slots_count()} covered slots."
            )
            return True
        except Exception as e:
            logger.warning(f"[WeeklyCoverageTracker] Could not load state from {self.cache_file}: {e}", exc_info=True)
            return False

    def reset(self) -> None:
        """Clears in-memory coverage matrix and removes persisted cache file."""
        self.slots = self._initialize_empty_matrix()
        self.total_recorded_steps = 0
        self.start_timestamp = None
        self.last_timestamp = None
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except OSError:
                pass

    @staticmethod
    def _initialize_empty_matrix() -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Creates an empty 7-day x 24-hour observation matrix."""
        matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for day in range(7):
            matrix[str(day)] = {}
            for hour in range(24):
                matrix[str(day)][str(hour)] = {
                    "steps": 0,
                    "reward_sum": 0.0,
                    "samples": 0,
                }
        return matrix
