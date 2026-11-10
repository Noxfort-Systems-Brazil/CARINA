# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional


class Trainer:
    """
    Pure Facade for the CARINA AI Engine process.
    Coordinates service lifecycle startup and delegates scenario loading.
    Adheres strictly to SOLID, Clean Architecture, and DDD.
    """

    def __init__(
        self,
        scenario_loader: Any,
        event_router: Optional[Any],
        pipe_conn: Any,
        connection_manager: Optional[Any] = None,
        action_supervisor: Optional[Any] = None,
        state_reconciler: Optional[Any] = None,
    ) -> None:
        self.scenario_loader = scenario_loader
        self.event_router = event_router
        self.pipe_conn = pipe_conn
        self.is_running = True
        self._connection_manager = connection_manager
        self._action_supervisor = action_supervisor
        self._state_reconciler = state_reconciler

    @property
    def action_supervisor(self) -> Optional[Any]:
        """Provides access to the action supervisor."""
        if self._action_supervisor is not None:
            return self._action_supervisor
        if self.event_router and hasattr(self.event_router, "step_processor"):
            return getattr(self.event_router.step_processor, "action_supervisor", None)
        return None

    @action_supervisor.setter
    def action_supervisor(self, val: Any) -> None:
        self._action_supervisor = val

    @property
    def connection_manager(self) -> Optional[Any]:
        """Provides access to the hardware connection manager."""
        if self._connection_manager is not None:
            return self._connection_manager
        supervisor = self.action_supervisor
        if supervisor and hasattr(supervisor, "connection_manager"):
            return supervisor.connection_manager
        try:
            from controller.connection_manager import HardwareConnectionManager

            return HardwareConnectionManager.get_instance()
        except Exception:
            return None

    @connection_manager.setter
    def connection_manager(self, val: Any) -> None:
        self._connection_manager = val

    @property
    def state_reconciler(self) -> Optional[Any]:
        """Provides access to the Fenix state reconciler."""
        if self._state_reconciler is not None:
            return self._state_reconciler
        if self.event_router and hasattr(self.event_router, "step_processor"):
            return getattr(self.event_router.step_processor, "state_reconciler", None)
        return None

    @state_reconciler.setter
    def state_reconciler(self, val: Any) -> None:
        self._state_reconciler = val

    @property
    def agents(self) -> Dict[str, Any]:
        """Provides access to currently active simulation agents."""
        return self.scenario_loader.agents if self.scenario_loader else {}

    @property
    def strategist(self) -> Optional[Any]:
        """Provides access to the strategic multi-agent coordinator."""
        return self.scenario_loader.strategist if self.scenario_loader else None

    @property
    def guardians(self) -> Dict[str, Any]:
        """Provides access to active safety guardian instances."""
        return self.scenario_loader.guardians if self.scenario_loader else {}

    @property
    def current_map_path(self) -> Optional[str]:
        """Returns the currently loaded scenario net path."""
        return self.scenario_loader.current_map_path if self.scenario_loader else None

    def start_continuous_service(self) -> None:
        """Signals backend readiness to Central Controller and enters the event loop."""
        try:
            if self.pipe_conn:
                self.pipe_conn.send(("system", "backend_ready", (), {}))
        except Exception as e:
            logging.error(f"[Trainer] Erro ao enviar sinal de backend_ready: {e}", exc_info=True)

        if self.event_router:
            self.event_router.start_continuous_service()

    def _load_map(self, map_path: str) -> None:
        """Delegates scenario initialization and topology loading to ScenarioLoader."""
        if self.scenario_loader:
            self.scenario_loader.load_scenario(map_path)
