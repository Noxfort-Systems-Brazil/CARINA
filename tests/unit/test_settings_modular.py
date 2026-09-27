# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_settings_modular.py
# Author: Gabriel Moraes
# Date: 2026-09-12

import configparser
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

try:
    from settings.env_provider import DotenvSecretProvider
    from settings.ini_storage import IniFileStorage
    from settings.interfaces import IEnvironmentProvider, ISettingsReader, ISettingsStorage, ISettingsWriter
    from settings.schema import SettingsSchema
    from settings.service import SettingsService
    from utils.settings_manager import SettingsManager
except ImportError:
    from src.settings.env_provider import DotenvSecretProvider
    from src.settings.ini_storage import IniFileStorage
    from src.settings.interfaces import IEnvironmentProvider, ISettingsReader, ISettingsStorage, ISettingsWriter
    from src.settings.schema import SettingsSchema
    from src.settings.service import SettingsService
    from src.utils.settings_manager import SettingsManager


class TestSettingsSchema(unittest.TestCase):
    def setUp(self):
        self.schema = SettingsSchema()

    def test_default_key_mapping(self):
        self.assertEqual(self.schema.get_section("theme_dark"), "UI")
        self.assertEqual(self.schema.get_section("green_time"), "TRAFFIC_RULES")
        self.assertEqual(self.schema.get_section("monitor_mqtt_host"), "EXTERNAL_MONITOR")
        self.assertIsNone(self.schema.get_section("non_existent_key"))

    def test_register_key_ocp(self):
        self.schema.register_key("custom_ai_param", "CUSTOM_AI", is_boolean=True)
        self.assertEqual(self.schema.get_section("custom_ai_param"), "CUSTOM_AI")
        self.assertTrue(self.schema.is_boolean_key("custom_ai_param"))

    def test_boolean_and_secret_keys(self):
        self.assertTrue(self.schema.is_boolean_key("theme_dark"))
        self.assertTrue(self.schema.is_boolean_key("log_progress"))
        self.assertTrue(self.schema.is_secret_key("db_password"))
        self.assertTrue(self.schema.is_secret_key("db_name"))
        self.assertTrue(self.schema.is_secret_key("db_host"))
        self.assertTrue(self.schema.is_secret_key("monitor_mqtt_host"))
        self.assertFalse(self.schema.is_secret_key("theme_dark"))

    def test_normalize_report_aliases(self):
        sample = {
            "xai_report_title": "City Report",
            "report_city": "Brasilia",
        }
        normalized = self.schema.normalize_report_aliases(sample)
        self.assertEqual(normalized["report_report_title"], "City Report")
        self.assertEqual(normalized["xai_city"], "Brasilia")


class TestIniFileStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ini_path = os.path.join(self.temp_dir.name, "test_settings.ini")
        self.storage = IniFileStorage(self.ini_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_not_found_raises(self):
        self.assertFalse(self.storage.exists())
        with self.assertRaises(FileNotFoundError):
            self.storage.read_config()

    def test_write_and_read_config(self):
        config = configparser.ConfigParser()
        config.add_section("UI")
        config.set("UI", "theme_dark", "True")

        saved = self.storage.write_config(config)
        self.assertTrue(saved)
        self.assertTrue(self.storage.exists())

        loaded_config = self.storage.read_config()
        self.assertTrue(loaded_config.has_section("UI"))
        self.assertEqual(loaded_config.get("UI", "theme_dark"), "True")


class TestDotenvSecretProvider(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = os.path.join(self.temp_dir.name, ".env")
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write("CARINA_DB_USER=test_carina_user\n")
            f.write("CARINA_MQTT_HOST=127.0.0.1\n")
        self.provider = DotenvSecretProvider(self.env_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_overrides(self):
        with patch.dict(os.environ, {"CARINA_DB_USER": "test_carina_user", "CARINA_MQTT_HOST": "127.0.0.1"}):
            overrides = self.provider.get_overrides()
            self.assertEqual(overrides.get("db_user"), "test_carina_user")
            self.assertEqual(overrides.get("monitor_mqtt_host"), "127.0.0.1")

    def test_sync_variable(self):
        success = self.provider.sync_variable("CARINA_MQTT_HOST", "https://new-monitor.com/api/telemetry")
        self.assertTrue(success)
        self.assertEqual(os.environ.get("CARINA_MQTT_HOST"), "https://new-monitor.com/api/telemetry")

        with open(self.env_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("CARINA_MQTT_HOST=https://new-monitor.com/api/telemetry", content)


class TestSettingsService(unittest.TestCase):
    def setUp(self):
        self.mock_storage = MagicMock(spec=ISettingsStorage)
        self.mock_env = MagicMock(spec=IEnvironmentProvider)
        self.schema = SettingsSchema()

        self.service = SettingsService(
            storage=self.mock_storage,
            env_provider=self.mock_env,
            schema=self.schema,
        )

    def test_load_settings_merges_storage_and_env(self):
        cfg = configparser.ConfigParser()
        cfg.add_section("UI")
        cfg.set("UI", "theme_dark", "true")
        cfg.add_section("TRAFFIC_RULES")
        cfg.set("TRAFFIC_RULES", "green_time", "30")

        self.mock_storage.read_config.return_value = cfg
        self.mock_env.get_overrides.return_value = {"monitor_mqtt_host": "https://monitor.com/api"}

        settings = self.service.load_settings()
        self.assertTrue(settings.get("theme_dark"))
        self.assertEqual(settings.get("green_time"), "30")
        self.assertEqual(settings.get("monitor_mqtt_host"), "https://monitor.com/api")

    def test_typed_getters(self):
        cfg = configparser.ConfigParser()
        cfg.add_section("UI")
        cfg.set("UI", "theme_dark", "true")
        cfg.add_section("TRAFFIC_RULES")
        cfg.set("TRAFFIC_RULES", "green_time", "45")

        self.mock_storage.read_config.return_value = cfg
        self.mock_env.get_overrides.return_value = {}

        self.assertTrue(self.service.get_bool("theme_dark"))
        self.assertEqual(self.service.get_int("green_time"), 45)
        self.assertEqual(self.service.get_float("green_time"), 45.0)
        self.assertEqual(self.service.get("non_existent", "default_val"), "default_val")

    def test_save_settings_syncs_monitor_host(self):
        cfg = configparser.ConfigParser()
        self.mock_storage.read_config.return_value = cfg
        self.mock_storage.write_config.return_value = True
        self.mock_env.has_env_file.return_value = True

        new_settings = {
            "green_time": 40,
            "monitor_mqtt_host": "https://remote-ngrok.io/api/telemetry",
            "db_password": "secret_pwd",
            "db_name": "prod_db",
        }

        success = self.service.save_settings(new_settings)
        self.assertTrue(success)
        self.mock_env.sync_variable.assert_any_call("CARINA_MQTT_HOST", "https://remote-ngrok.io/api/telemetry")
        self.mock_env.sync_variable.assert_any_call("CARINA_DB_PASSWORD", "secret_pwd")
        self.mock_env.sync_variable.assert_any_call("CARINA_DB_NAME", "prod_db")
        self.assertEqual(cfg.get("TRAFFIC_RULES", "green_time"), "40")
        self.assertFalse(cfg.has_option("DATABASE", "db_password"))
        self.assertFalse(cfg.has_option("DATABASE", "db_name"))
        self.assertFalse(cfg.has_option("EXTERNAL_MONITOR", "monitor_mqtt_host"))


class TestSettingsManagerFacade(unittest.TestCase):
    def test_facade_compatibility(self):
        sm = SettingsManager()
        self.assertIsInstance(sm, SettingsService)
        self.assertIsInstance(sm, ISettingsReader)
        self.assertIsInstance(sm, ISettingsWriter)
        self.assertTrue(hasattr(sm, "load_config"))
        self.assertTrue(hasattr(sm, "load_settings"))
        self.assertTrue(hasattr(sm, "save_settings"))
        self.assertTrue(hasattr(sm, "_KEY_TO_SECTION_MAP"))
        self.assertIn("theme_dark", sm._KEY_TO_SECTION_MAP)
        self.assertTrue(hasattr(sm, "config_path"))

        cfg = sm.load_config()
        self.assertIsInstance(cfg, configparser.ConfigParser)
        self.assertTrue(hasattr(cfg, "getint"))


if __name__ == "__main__":
    unittest.main()
