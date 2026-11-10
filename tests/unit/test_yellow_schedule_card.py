# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from ui.cards.yellow_schedule_card import YellowScheduleCard


class TestYellowScheduleCard:

    def test_initialization_defaults(self):
        initial = {
            "yellow_schedule_enabled": True,
            "yellow_schedule_start": "22:00",
            "yellow_schedule_end": "04:30",
            "yellow_schedule_all_semaphores": False,
            "yellow_schedule_semaphores": "J1, J2",
        }

        card = YellowScheduleCard(initial)

        assert card.switch_enabled.value is True
        assert card.tf_start.value == "22:00"
        assert card.tf_end.value == "04:30"
        assert card.switch_all.value is False
        assert card.tf_semaphores.value == "J1, J2"
        assert card.schedule_body.visible is True
        assert card.semaphores_container.visible is True

    def test_get_values(self):
        initial = {
            "yellow_schedule_enabled": True,
            "yellow_schedule_start": "23:00",
            "yellow_schedule_end": "05:00",
            "yellow_schedule_all_semaphores": True,
            "yellow_schedule_semaphores": "J1",
        }

        card = YellowScheduleCard(initial)
        values = card.get_values()

        assert values["yellow_schedule_enabled"] is True
        assert values["yellow_schedule_start"] == "23:00"
        assert values["yellow_schedule_end"] == "05:00"
        assert values["yellow_schedule_all_semaphores"] is True
        assert values["yellow_schedule_semaphores"] == "J1"

    def test_set_values(self):
        card = YellowScheduleCard({})

        card.set_values({
            "yellow_schedule_enabled": True,
            "yellow_schedule_start": "01:00",
            "yellow_schedule_end": "06:00",
            "yellow_schedule_all_semaphores": False,
            "yellow_schedule_semaphores": "TL_A, TL_B",
        })

        values = card.get_values()
        assert values["yellow_schedule_enabled"] is True
        assert values["yellow_schedule_start"] == "01:00"
        assert values["yellow_schedule_end"] == "06:00"
        assert values["yellow_schedule_all_semaphores"] is False
        assert values["yellow_schedule_semaphores"] == "TL_A, TL_B"

    def test_validation_valid_times(self):
        card = YellowScheduleCard({
            "yellow_schedule_enabled": True,
            "yellow_schedule_start": "23:00",
            "yellow_schedule_end": "05:00",
        })

        assert card.validate_fields() is True
        assert card.tf_start.error_text is None
        assert card.tf_end.error_text is None

    def test_validation_invalid_times(self):
        card = YellowScheduleCard({
            "yellow_schedule_enabled": True,
            "yellow_schedule_start": "25:00",
            "yellow_schedule_end": "05:70",
        })

        assert card.validate_fields() is False
        assert card.tf_start.error_text is not None

    def test_chips_selection_and_toggling(self):
        card = YellowScheduleCard({
            "yellow_schedule_enabled": True,
            "yellow_schedule_semaphores": "J1",
        })

        card.set_available_intersections(["J1", "J2", "J3"])

        assert len(card.chips_row.controls) == 3
        assert card._selected_ids == {"J1"}

        # Select J2
        card._toggle_chip("J2", True)
        assert card._selected_ids == {"J1", "J2"}
        assert "J1" in card.tf_semaphores.value
        assert "J2" in card.tf_semaphores.value

        # Deselect J1
        card._toggle_chip("J1", False)
        assert card._selected_ids == {"J2"}
        assert card.tf_semaphores.value == "J2"
