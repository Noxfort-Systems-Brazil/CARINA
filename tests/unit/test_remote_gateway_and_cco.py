# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import threading
import time
import unittest
from unittest.mock import MagicMock

from src.settings.schema import SettingsSchema
from ui.cards.remote_gateway_card import RemoteGatewayCard
from ui.handlers.settings_defaults import DEFAULT_SETTINGS_MAP, KEY_TO_SECTION_MAP


class TestRemoteGatewayAndCCO(unittest.TestCase):
    """Unit tests for Remote Gateway subsystem (Tailscale Funnel) and CCO Narrator."""

    def test_schema_contains_remote_gateway_keys(self):
        expected_keys = [
            "gateway_enabled",
            "cco_subdomain",
            "evp_subdomain",
            "evp_auth_token",
            "cco_port",
            "evp_port",
        ]
        for key in expected_keys:
            self.assertIn(key, SettingsSchema.DEFAULT_KEY_TO_SECTION_MAP)
            self.assertEqual(SettingsSchema.DEFAULT_KEY_TO_SECTION_MAP[key], "REMOTE_GATEWAY")
            self.assertIn(key, KEY_TO_SECTION_MAP)
            self.assertEqual(KEY_TO_SECTION_MAP[key], "REMOTE_GATEWAY")
            self.assertIn(key, DEFAULT_SETTINGS_MAP)

    def test_remote_gateway_card_get_and_set_values(self):
        initial = {
            "gateway_enabled": False,
        }
        mock_ctrl = MagicMock()
        mock_ctrl.format_service_urls.return_value = {
            "domain": "carina-node.tail08aec6.ts.net",
            "cco_url": "https://carina-node.tail08aec6.ts.net/cco",
            "evp_url": "https://carina-node.tail08aec6.ts.net/amb/v1",
        }
        card = RemoteGatewayCard(initial, controller=mock_ctrl)
        values = card.get_values()

        self.assertFalse(values["gateway_enabled"])

        try:
            # Test manual connection in RAM
            card._handle_connect(None)
            self.assertTrue(card.get_values()["gateway_enabled"])

            # Update values via set_values
            new_values = {
                "gateway_enabled": True,
            }
            card.set_values(new_values)
            updated = card.get_values()
            self.assertTrue(updated["gateway_enabled"])

            # Post-test cleanup
            card._handle_disconnect(None)
            self.assertFalse(card.get_values()["gateway_enabled"])
        finally:
            card._handle_disconnect(None)
            card.set_values(initial)

    def test_go_event_dispatcher_evp_telemetry(self):
        from src.drivers.go_event_dispatcher import GoEventDispatcher
        from src.evp.evp_models import CorporationType, RegisteredVehicle
        from src.evp.evp_service import EVPService

        EVPService.get_instance().register_fleet_vehicle(
            RegisteredVehicle(vehicle_id="TEST-SAMU-99", corporation=CorporationType.SAMU)
        )

        dispatcher = GoEventDispatcher()
        event_data = {
            "type": "event",
            "event_type": "evp_telemetry",
            "payload": {
                "vehicle_id": "TEST-SAMU-99",
                "corporation": "SAMU",
                "latitude": -23.5505,
                "longitude": -46.6333,
                "speed_kmh": 70.0,
                "heading_deg": 90.0,
                "siren_active": True,
            },
        }
        dispatcher.dispatch(event_data)

        vehicles = EVPService.get_instance().get_all_vehicles()
        test_v = next((v for v in vehicles if v.get("vehicle_id") == "TEST-SAMU-99"), None)
        self.assertIsNotNone(test_v)
        self.assertEqual(test_v.get("corporation"), "SAMU")

    def test_remote_gateway_controller_domain_and_urls(self):
        from ui.controllers.remote_gateway_controller import RemoteGatewayController

        controller = RemoteGatewayController()
        # Domain sanitization
        self.assertEqual(
            controller.clean_domain("https://meu-carina.tail08aec6.ts.net./"),
            "meu-carina.tail08aec6.ts.net",
        )
        self.assertEqual(
            controller.clean_domain("meu-carina.tail08aec6.ts.net"),
            "meu-carina.tail08aec6.ts.net",
        )

        # URL formatting
        urls = controller.format_service_urls("carina-teste.tail08aec6.ts.net")
        self.assertEqual(urls["cco_url"], "https://carina-teste.tail08aec6.ts.net/cco")
        self.assertEqual(urls["evp_url"], "https://carina-teste.tail08aec6.ts.net/amb/v1")

    def test_remote_gateway_controller_async_operations(self):
        from ui.controllers.remote_gateway_controller import RemoteGatewayController

        mock_go = MagicMock()
        mock_go.is_running.return_value = True
        mock_go.send_command.return_value = {
            "success": True,
            "data": {"domain": "carina-node.tail08aec6.ts.net", "funnel_active": True},
        }

        controller = RemoteGatewayController(go_client=mock_go)

        # 1. Asynchronous connection test
        test_results = []
        test_done = threading.Event()
        controller.test_connection_async(lambda ok, msg: (test_results.append((ok, msg)), test_done.set()))
        self.assertTrue(test_done.wait(timeout=2.0))
        self.assertTrue(len(test_results) > 0)
        self.assertTrue(test_results[0][0])
        mock_go.send_command.assert_called_with("tailscale_status", timeout=8.0)

        # 2. Asynchronous connection
        connect_results = []
        connect_done = threading.Event()
        controller.connect_gateway_async(lambda ok, msg: (connect_results.append((ok, msg)), connect_done.set()))
        self.assertTrue(connect_done.wait(timeout=2.0))
        self.assertTrue(len(connect_results) > 0)
        self.assertTrue(connect_results[0][0])
        mock_go.start.assert_called()
        mock_go.send_command.assert_called_with("gateway_set_enabled", timeout=5.0, enabled=True)

        # 3. Disconnection
        controller.disconnect_gateway()
        mock_go.send_command.assert_called_with("gateway_set_enabled", timeout=5.0, enabled=False)

    def test_remote_endpoints_banner_component(self):
        from ui.components.remote_endpoints_banner import RemoteEndpointsBanner

        copied = []
        banner = RemoteEndpointsBanner(
            initial_cco_url="https://init.tail08aec6.ts.net/cco",
            initial_evp_url="https://init.tail08aec6.ts.net/amb/v1",
            on_copy=lambda url, lbl: copied.append((url, lbl)),
        )

        self.assertEqual(banner.cco_path_text.value, "https://init.tail08aec6.ts.net/cco")
        self.assertEqual(banner.evp_path_text.value, "https://init.tail08aec6.ts.net/amb/v1")

        # Dynamic URL update
        banner.update_urls("https://novo.tail08aec6.ts.net/cco", "https://novo.tail08aec6.ts.net/amb/v1")
        self.assertEqual(banner.cco_path_text.value, "https://novo.tail08aec6.ts.net/cco")
        self.assertEqual(banner.evp_path_text.value, "https://novo.tail08aec6.ts.net/amb/v1")

        # Copy
        banner._handle_copy("https://novo.tail08aec6.ts.net/cco", "Link CCO")
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0][0], "https://novo.tail08aec6.ts.net/cco")
        self.assertEqual(copied[0][1], "Link CCO")


if __name__ == "__main__":
    unittest.main()
