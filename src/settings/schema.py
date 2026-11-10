# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Encapsulates configuration metadata, key-to-section mappings, and schema rules.
Complies with Single Responsibility Principle (SRP) and Open/Closed Principle (OCP).
"""

from typing import Any, Dict, Optional, Set


class SettingsSchema:
    """Manages the catalog of configuration keys, sections, types, and domain aliases."""

    DEFAULT_KEY_TO_SECTION_MAP: Dict[str, str] = {
        "theme_dark": "UI",
        "language": "UI",
        "min_green_time": "TRAFFIC_RULES",
        "green_time": "TRAFFIC_RULES",
        "yellow_time": "TRAFFIC_RULES",
        "yellow_time_seconds": "TRAFFIC_RULES",
        "heatmap_strategy": "HEATMAP_SCALING",
        "heatmap_saturation": "HEATMAP_SCALING",
        "log_progress": "LOGGING",
        "watchdog_grace": "WATCHDOG",
        "analysis_interval_value": "ANALYSIS_SCHEDULE",
        "analysis_interval_unit": "ANALYSIS_SCHEDULE",
        "performance_margin": "MATURITY",
        "auto_pacing_enabled": "MATURITY",
        "auto_performance_margin_enabled": "MATURITY",
        "child_phase_episodes": "MATURITY",
        "teen_phase_min_episodes": "MATURITY",
        "child_promotion_max_entropy": "MATURITY",
        "performance_check_window": "MATURITY",
        "calibration_window_size": "CALIBRATION",
        "telemetry_delta_ms": "AI_TRAINING",
        "episode_max_steps": "AI_TRAINING",
        "ppo_gamma": "AI_TRAINING",
        "ppo_k_epochs": "AI_TRAINING",
        "ppo_eps_clip": "AI_TRAINING",
        "dqn_epsilon_decay": "GUARDIAN_AGENT",
        "dqn_batch_size": "GUARDIAN_AGENT",
        "pbt_frequency": "PBT",
        "pbt_exploitation": "PBT",
        "weight_waiting_time": "REWARD_WEIGHTS",
        "weight_flow": "REWARD_WEIGHTS",
        "auto_reward_weights_enabled": "REWARD_WEIGHTS",
        "weight_emergency_brake": "REWARD_WEIGHTS",
        "weight_teleport": "REWARD_WEIGHTS",
        "update_frequency_seconds": "GAT_STRATEGIST",
        # CARINA Monitor Integration
        "monitor_enabled": "EXTERNAL_MONITOR",
        "monitor_mqtt_host": "EXTERNAL_MONITOR",
        "monitor_mqtt_port": "EXTERNAL_MONITOR",
        "monitor_mqtt_topic_heartbeat": "EXTERNAL_MONITOR",
        "monitor_mqtt_topic_incident": "EXTERNAL_MONITOR",
        # CARINA Remote Gateway (Tailscale Funnel)
        "gateway_enabled": "REMOTE_GATEWAY",
        "cco_subdomain": "REMOTE_GATEWAY",
        "evp_subdomain": "REMOTE_GATEWAY",
        "evp_auth_token": "REMOTE_GATEWAY",
        "cco_port": "REMOTE_GATEWAY",
        "evp_port": "REMOTE_GATEWAY",
        # CARINA Database Settings
        "db_type": "DATABASE",
        "db_host": "DATABASE",
        "db_port": "DATABASE",
        "db_user": "DATABASE",
        "db_password": "DATABASE",
        "db_name": "DATABASE",
        "db_connected": "DATABASE",
        "tensorboard_enabled": "TENSORBOARD",
        "tensorboard_log_dir": "TENSORBOARD",
        # CARINA Universal Report Formatting Settings
        "decimal_separator": "REPORT_FORMATTING",
        "report_logo_path": "REPORT_FORMATTING",
        "report_city": "REPORT_FORMATTING",
        "report_state_uf": "REPORT_FORMATTING",
        "report_secretary_name": "REPORT_FORMATTING",
        "report_secretary_title": "REPORT_FORMATTING",
        "report_agency_name": "REPORT_FORMATTING",
        "report_department_name": "REPORT_FORMATTING",
        "report_title": "REPORT_FORMATTING",
        "report_block_order": "REPORT_FORMATTING",
        "report_font_name": "REPORT_FORMATTING",
        "report_font_size": "REPORT_FORMATTING",
        "report_margin_top": "REPORT_FORMATTING",
        "report_margin_bottom": "REPORT_FORMATTING",
        "report_margin_left": "REPORT_FORMATTING",
        "report_margin_right": "REPORT_FORMATTING",
        "report_line_spacing": "REPORT_FORMATTING",
        "report_alignment": "REPORT_FORMATTING",
        "report_speed_unit": "REPORT_FORMATTING",
        "report_ordinance_enabled": "REPORT_FORMATTING",
        "report_ordinance_number": "REPORT_FORMATTING",
        "report_slm_device": "REPORT_FORMATTING",
        "report_slm_gpu_layers": "REPORT_FORMATTING",
        # Legacy XAI key aliases mapped to REPORT_FORMATTING section
        "xai_logo_path": "REPORT_FORMATTING",
        "xai_secretary_name": "REPORT_FORMATTING",
        "xai_secretary_title": "REPORT_FORMATTING",
        "xai_agency_name": "REPORT_FORMATTING",
        "xai_department_name": "REPORT_FORMATTING",
        "xai_report_title": "REPORT_FORMATTING",
        "xai_block_order": "REPORT_FORMATTING",
        "xai_font_name": "REPORT_FORMATTING",
        "xai_font_size": "REPORT_FORMATTING",
        "xai_margin_top": "REPORT_FORMATTING",
        "xai_margin_bottom": "REPORT_FORMATTING",
        "xai_margin_left": "REPORT_FORMATTING",
        "xai_margin_right": "REPORT_FORMATTING",
        "xai_line_spacing": "REPORT_FORMATTING",
        "xai_alignment": "REPORT_FORMATTING",
        "xai_speed_unit": "REPORT_FORMATTING",
        "xai_slm_device": "REPORT_FORMATTING",
        "xai_slm_gpu_layers": "REPORT_FORMATTING",
        # Yellow Flashing Schedule Settings
        "yellow_schedule_enabled": "YELLOW_SCHEDULE",
        "yellow_schedule_start": "YELLOW_SCHEDULE",
        "yellow_schedule_end": "YELLOW_SCHEDULE",
        "yellow_schedule_all_semaphores": "YELLOW_SCHEDULE",
        "yellow_schedule_semaphores": "YELLOW_SCHEDULE",
        # EVP Settings
        "auto_register_fleet": "EVP",
    }

    DEFAULT_BOOLEAN_KEYS: Set[str] = {
        "auto_register_fleet",
        "theme_dark",
        "log_progress",
        "monitor_enabled",
        "gateway_enabled",
        "tensorboard_enabled",
        "report_ordinance_enabled",
        "xai_ordinance_enabled",
        "yellow_schedule_enabled",
        "yellow_schedule_all_semaphores",
        "auto_pacing_enabled",
        "auto_performance_margin_enabled",
        "auto_reward_weights_enabled",
        "db_connected",
    }

    PROTECTED_ENV_KEYS: Set[str] = {
        "db_password",
        "db_user",
        "db_host",
        "db_port",
        "db_name",
        "db_schema",
        "monitor_mqtt_host",
        "monitor_mqtt_port",
    }

    SECRET_KEYS: Set[str] = PROTECTED_ENV_KEYS

    def __init__(self, key_to_section_map: Optional[Dict[str, str]] = None):
        self._key_map: Dict[str, str] = dict(key_to_section_map or self.DEFAULT_KEY_TO_SECTION_MAP)
        self._boolean_keys: Set[str] = set(self.DEFAULT_BOOLEAN_KEYS)

    @property
    def key_map(self) -> Dict[str, str]:
        """Returns an immutable or copy view of the key-to-section mapping."""
        return dict(self._key_map)

    def register_key(self, key: str, section: str, is_boolean: bool = False) -> None:
        """Dynamically registers a configuration key and section (Open/Closed Principle)."""
        self._key_map[key] = section
        if is_boolean:
            self._boolean_keys.add(key)

    def get_section(self, key: str) -> Optional[str]:
        """Returns the INI section name for a given key, or None if unmapped."""
        return self._key_map.get(key)

    def is_boolean_key(self, key: str) -> bool:
        """Checks if a key is registered as boolean."""
        return key in self._boolean_keys

    def is_secret_key(self, key: str) -> bool:
        """Checks if a key represents a sensitive credential managed outside INI."""
        return key in self.SECRET_KEYS

    def normalize_report_aliases(self, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures bidirectional compatibility between legacy 'xai_' prefixes
        and unified 'report_' prefixes.
        """
        for k, v in list(settings_dict.items()):
            if k.startswith("xai_"):
                report_alias = "report_" + k[4:]
                if report_alias not in settings_dict:
                    settings_dict[report_alias] = v
            elif k.startswith("report_"):
                xai_alias = "xai_" + k[7:]
                if xai_alias not in settings_dict:
                    settings_dict[xai_alias] = v
        return settings_dict
