# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Isolated UI unit tests for Connection Cards:
- DatabaseSettingsCard
- RemoteGatewayCard
- MonitorSettingsCard
Segregates presentation unit tests from integration and persistence tests (SRP).
"""

from unittest.mock import MagicMock
import pytest

from ui.cards.database_settings_card import DatabaseSettingsCard
from ui.cards.monitor_settings_card import MonitorSettingsCard
from ui.cards.remote_gateway_card import RemoteGatewayCard


@pytest.mark.unit
def test_database_settings_card_persistence_and_no_destructive_silent_test():
    """
    Ensures DatabaseSettingsCard respects persisted state without triggering
    silent tests that overwrite is_connected to False.
    """
    initial_settings = {
        "db_connected": True,
        "db_type": "postgres",
        "db_host": "127.0.0.1",
        "db_port": "5432",
        "db_name": "carina_traffic",
        "db_user": "postgres",
        "db_password": "secure_password",
    }

    card = DatabaseSettingsCard(initial_values=initial_settings)

    # 1. Card should initialize as connected
    assert card.is_connected is True
    assert card.btn_connect.visible is False
    assert card.btn_disconnect.visible is True

    # 2. Failed background silent test callback should not disarm is_connected
    card._update_test_result(success=False, error_msg="Unreachable host (mocked)", silent_auto=True)
    assert card.is_connected is True

    # 3. set_values with True maintains active connection
    card.set_values(initial_settings)
    assert card.is_connected is True


@pytest.mark.unit
def test_remote_gateway_card_persistence_and_no_auto_connection_start():
    """
    Ensures RemoteGatewayCard loads connected state without starting
    unsolicited network threads in the constructor.
    """
    mock_controller = MagicMock()
    mock_controller.clean_domain.side_effect = lambda d: d
    mock_controller.format_service_urls.return_value = {
        "domain": "carina-node.tail08aec6.ts.net",
        "cco_url": "https://carina-node.tail08aec6.ts.net/cco",
        "evp_url": "https://carina-node.tail08aec6.ts.net/amb/v1",
    }

    initial_settings = {
        "gateway_enabled": True,
    }

    card = RemoteGatewayCard(
        initial_values=initial_settings,
        controller=mock_controller,
    )

    # Should not have called connect_gateway_async on bootstrap
    mock_controller.connect_gateway_async.assert_not_called()

    # Should mark as connected
    assert card.is_connected is True
    assert card.btn_connect.visible is False
    assert card.btn_disconnect.visible is True

    values = card.get_values()
    assert values["gateway_enabled"] is True


@pytest.mark.unit
def test_monitor_settings_card_persistence():
    """
    Ensures MonitorSettingsCard reflects persisted connection status.
    """
    initial_settings = {
        "monitor_enabled": "True",
        "monitor_mqtt_host": "192.168.1.150:1883",
    }

    card = MonitorSettingsCard(initial_values=initial_settings)

    assert card.is_connected is True
    assert card.tf_host.disabled is True
    assert card.btn_connect.visible is False
    assert card.btn_disconnect.visible is True

    values = card.get_values()
    assert values["monitor_enabled"] == "True"
    assert values["monitor_mqtt_host"] == "192.168.1.150:1883"
