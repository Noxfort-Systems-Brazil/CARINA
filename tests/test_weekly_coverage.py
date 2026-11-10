# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for WeeklyCoverageTracker.
Verifies slot distribution, persistence across restart, and 1-week coverage completion logic.
"""

from datetime import datetime, timezone
import os
import tempfile
import pytest

from src.core.weekly_coverage_tracker import WeeklyCoverageTracker


def test_slot_recording_with_known_datetime():
    """Verifies that epoch timestamp maps correctly to calendar day and hour."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tracker = WeeklyCoverageTracker(cache_dir=tmp_dir, phase_name="CHILD")

        # Wednesday, October 21, 2026 at 14:30:00 UTC
        # weekday() = 2 (Wednesday), hour = 14 (in UTC)
        # We test with local datetime equivalent
        dt = datetime(2026, 10, 21, 14, 30, 0)
        ts = dt.timestamp()

        day_idx, hour_idx = tracker.record_step(raw_timestamp=ts, reward=2.5)

        assert day_idx == dt.weekday()
        assert hour_idx == dt.hour

        slot = tracker.slots[str(day_idx)][str(hour_idx)]
        assert slot["steps"] == 1
        assert slot["samples"] == 1
        assert slot["reward_sum"] == 2.5


def test_atomic_persistence_and_resume():
    """Verifies that coverage state survives process termination and resumes correctly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tracker1 = WeeklyCoverageTracker(cache_dir=tmp_dir, phase_name="CHILD")

        # Record 100 steps on Monday at 08:00
        dt_mon_08 = datetime(2026, 10, 19, 8, 15, 0).timestamp()
        for _ in range(100):
            tracker1.record_step(dt_mon_08, reward=1.0)

        # Record 50 steps on Friday at 18:00
        dt_fri_18 = datetime(2026, 10, 23, 18, 45, 0).timestamp()
        for _ in range(50):
            tracker1.record_step(dt_fri_18, reward=0.5)

        assert tracker1.save_to_disk() is True

        # Simulate fresh process restart by creating a new instance on the same cache directory
        tracker2 = WeeklyCoverageTracker(cache_dir=tmp_dir, phase_name="CHILD")

        assert tracker2.total_recorded_steps == 150
        assert tracker2.get_covered_slots_count(min_steps_per_slot=50) == 2
        assert tracker2.get_covered_slots_count(min_steps_per_slot=100) == 1


def test_weekly_completion_criteria():
    """Validates that week completion requires 95% of discrete slots to be covered."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tracker = WeeklyCoverageTracker(cache_dir=tmp_dir, phase_name="TEEN")

        # Initially incomplete
        completed, pct, stats = tracker.is_week_completed(min_steps_per_slot=10)
        assert completed is False
        assert pct == 0.0

        # Fill 160 of the 168 slots (160 / 168 = 95.2%)
        slot_idx = 0
        base_dt = datetime(2026, 10, 19, 0, 0, 0)
        for day in range(7):
            for hour in range(24):
                if slot_idx < 160:
                    dt = datetime(2026, 10, 19 + day, hour, 0, 0)
                    for _ in range(10):
                        tracker.record_step(dt.timestamp(), reward=1.0)
                slot_idx += 1

        completed, pct, stats = tracker.is_week_completed(min_steps_per_slot=10, required_coverage_pct=0.95)
        assert completed is True
        assert pct >= 0.95
        assert stats["covered_slots"] == 160
