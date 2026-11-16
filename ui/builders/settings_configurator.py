# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import flet as ft

from src.controller.connection_manager import HardwareConnectionManager
from src.evp.evp_service import EVPService
from ui.cards.account_settings_card import AccountSettingsCard
from ui.cards.advanced_dqn_card import AdvancedDQNCard
from ui.cards.advanced_ppo_card import AdvancedPPOCard
from ui.cards.advanced_system_card import AdvancedSystemCard
from ui.cards.dashboard_settings_card import DashboardSettingsCard
from ui.cards.database_settings_card import DatabaseSettingsCard
from ui.cards.evp_fleet_connection_card import EVPFleetConnectionCard
from ui.cards.general_settings_card import GeneralSettingsCard
from ui.cards.hardware_connection_card import HardwareConnectionCard
from ui.cards.monitor_settings_card import MonitorSettingsCard
from ui.cards.piloting_school_card import PilotingSchoolCard
from ui.cards.remote_gateway_card import RemoteGatewayCard
from ui.cards.report_formatting_card import ReportFormattingCard
from ui.cards.reward_weights_card import RewardWeightsCard
from ui.cards.traffic_rules_card import TrafficRulesCard
from ui.cards.yellow_schedule_card import YellowScheduleCard
from ui.handlers.account_settings_handler import AccountSettingsHandler
from ui.handlers.evp_settings_handler import EVPSettingsHandler
from ui.handlers.hardware_settings_handler import HardwareSettingsHandler
from ui.handlers.monitor_settings_handler import MonitorSettingsHandler
from ui.handlers.settings_handler import SettingsHandler
from ui.views.settings_view import SettingsView


def build_settings_view(locale_manager, settings_client):
    """
    OCP: Constructs and wires the tabs and cards for SettingsView.
    To add a new setting tab or card, modify only this builder.
    """
    handler = SettingsHandler()
    initial_settings = handler.get_current_settings()

    # Handlers
    hardware_handler = HardwareSettingsHandler(
        HardwareConnectionManager.get_instance(locale_manager=locale_manager),
        settings_client,
        locale_manager=locale_manager,
    )
    evp_handler = EVPSettingsHandler(
        EVPService.get_instance(),
        settings_client,
        locale_manager=locale_manager,
    )
    account_handler = AccountSettingsHandler(settings_client)
    monitor_handler = MonitorSettingsHandler(settings_client)

    # Cards
    formatting_card = ReportFormattingCard(initial_settings)
    general_card = GeneralSettingsCard(initial_settings)
    traffic_rules_card = TrafficRulesCard(initial_settings)
    yellow_schedule_card = YellowScheduleCard(initial_settings, locale_manager=locale_manager)
    dashboard_card = DashboardSettingsCard(initial_settings)
    advanced_ppo_card = AdvancedPPOCard(initial_settings)
    advanced_dqn_card = AdvancedDQNCard(initial_settings)
    advanced_system_card = AdvancedSystemCard(initial_settings)
    piloting_school_card = PilotingSchoolCard(initial_settings)
    reward_weights_card = RewardWeightsCard(initial_settings)

    def _on_monitor_connection_toggle(enabled: bool, host: str):
        monitor_handler.on_monitor_toggle(enabled, host)
        payload = {"monitor_enabled": str(enabled), "monitor_mqtt_host": host}
        handler.prepare_settings_for_save(payload)

    monitor_card = MonitorSettingsCard(
        initial_values=initial_settings,
        on_toggle_connection=_on_monitor_connection_toggle,
        locale_manager=locale_manager,
    )

    hardware_card = HardwareConnectionCard(
        on_import_click=hardware_handler.on_import_click,
        on_export_click=hardware_handler.on_export_click,
        on_toggle_connection=hardware_handler.on_toggle_connection,
        locale_manager=locale_manager,
    )

    account_card = AccountSettingsCard(
        locale_manager=locale_manager,
        on_add_user=account_handler.on_add_user,
        on_remove_user=account_handler.on_remove_user,
        on_request_list=account_handler.on_request_users_list,
    )

    def _on_db_connection_toggle(connected: bool):
        payload = {
            "db_connected": str(connected),
            "db_type": db_card.db_type_dropdown.value,
        }
        handler.prepare_settings_for_save(payload)

    db_card = DatabaseSettingsCard(
        initial_values=initial_settings,
        on_toggle_connection=_on_db_connection_toggle,
        locale_manager=locale_manager,
    )

    def _on_gateway_connection_toggle(connected: bool, values: dict):
        handler.prepare_settings_for_save(values)

    evp_connection_card = EVPFleetConnectionCard(
        locale_manager=locale_manager,
        handler=evp_handler,
    )
    from ui.controllers.remote_gateway_controller import RemoteGatewayController

    remote_gateway_card = RemoteGatewayCard(
        initial_settings,
        on_toggle_connection=_on_gateway_connection_toggle,
        locale_manager=locale_manager,
        controller=RemoteGatewayController(settings_client=settings_client),
    )

    warning_text = ft.Text(size=12, expand=True, italic=True)

    tab_definitions = [
        {
            "icon": ft.Icons.TUNE_ROUNDED,
            "title_key": "settings_view.tab_general",
            "default_title": "General",
            "cards": [general_card, db_card, traffic_rules_card, yellow_schedule_card, dashboard_card],
        },
        {
            "icon": ft.Icons.HUB_ROUNDED,
            "title_key": "settings_view.tab_advanced",
            "default_title": "Advanced",
            "cards": [
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER),
                    border=ft.border.all(1, ft.Colors.AMBER),
                    border_radius=10,
                    padding=15,
                    content=ft.Row([ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.AMBER), warning_text]),
                ),
                advanced_ppo_card,
                advanced_dqn_card,
                piloting_school_card,
                reward_weights_card,
                advanced_system_card,
            ],
        },
        {
            "icon": ft.Icons.CABLE_ROUNDED,
            "title_key": "settings_view.tab_hardware",
            "default_title": "Hardware",
            "is_dynamic_fallback": True,
            "cards": [hardware_card],
        },
        {
            "icon": ft.Icons.EMERGENCY_ROUNDED,
            "title_key": "settings_view.tab_evp",
            "default_title": "Preempção (EVP)",
            "cards": [evp_connection_card],
        },
        {
            "icon": ft.Icons.MONITOR_HEART_ROUNDED,
            "title_key": "settings_view.tab_monitor",
            "default_title": "Monitor",
            "is_dynamic_fallback": True,
            "cards": [monitor_card],
        },
        {
            "icon": ft.Icons.ROUTER_ROUNDED,
            "title_key": "settings_view.tab_remote_gateway",
            "default_title": "Acesso Remoto",
            "is_dynamic_fallback": True,
            "cards": [remote_gateway_card],
        },
        {
            "icon": ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
            "title_key": "settings_view.tab_accounts",
            "default_title": "Contas",
            "cards": [account_card],
        },
        {
            "icon": ft.Icons.PRINT_ROUNDED,
            "title_key": "settings_view.tab_formatting",
            "default_title": "Formatação",
            "cards": [formatting_card],
        },
    ]

    view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client,
        tab_definitions=tab_definitions,
        warning_text_ref=warning_text,
        handler=handler,
    )

    view.hardware_handler = hardware_handler
    view.hardware_card = hardware_card
    view.evp_handler = evp_handler
    view.evp_card = evp_connection_card
    view.account_card = account_card
    view.remote_gateway_card = remote_gateway_card

    return view
