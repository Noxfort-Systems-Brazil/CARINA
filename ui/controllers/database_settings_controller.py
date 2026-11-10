# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Optional

from ui.controllers.database_connection_tester import DatabaseConnectionTester


class DatabaseSettingsController:
    """Controller orchestrating database connection testing and state transitions."""

    def __init__(self, on_state_change: Optional[Callable[[str, Optional[str], bool], None]] = None):
        self.on_state_change = on_state_change
        self.is_testing = False

    def test_connection_async(
        self,
        config: Dict[str, Any],
        on_result: Callable[[bool, str, bool], None],
        silent_auto: bool = False,
    ) -> None:
        """Asynchronously tests connection parameters with callback notification."""
        self.is_testing = True

        def _internal_callback(success: bool, err_msg: str) -> None:
            self.is_testing = False
            on_result(success, err_msg, silent_auto)

        DatabaseConnectionTester.test_connection_async(
            db_type=config.get("db_type", "sqlite"),
            host=config.get("db_host", "localhost"),
            port=config.get("db_port", "5432"),
            user=config.get("db_user", "postgres"),
            password=config.get("db_password", ""),
            dbname=config.get("db_name", "carina_data"),
            callback=_internal_callback,
        )
