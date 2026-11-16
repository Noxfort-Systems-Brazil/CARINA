# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Settings persister for remote gateway enabled state (SRP / DIP).
Consolidates SettingsHandler (settings.ini), SettingsManager, DotenvSecretProvider (.env),
and backend notification outside RemoteGatewayController.
"""

import logging
from typing import Any, Callable, Optional

from src.interfaces.controller import IRemoteGatewayBackend

logger = logging.getLogger(__name__)


class RemoteGatewaySettingsPersister:
    """Persists `gateway_enabled` consistently across settings.ini, .env, and runtime backend."""

    def __init__(
        self,
        settings_manager: Optional[Any] = None,
        env_provider: Optional[Any] = None,
        settings_handler_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._settings_manager = settings_manager
        self._env_provider = env_provider
        self._settings_handler_factory = settings_handler_factory

    def _get_settings_manager(self) -> Optional[Any]:
        if self._settings_manager is None:
            from src.utils.settings_manager import SettingsManager

            self._settings_manager = SettingsManager()
        return self._settings_manager

    def _get_env_provider(self) -> Optional[Any]:
        if self._env_provider is None:
            try:
                from src.settings.env_provider import DotenvSecretProvider

                self._env_provider = DotenvSecretProvider()
            except Exception:
                pass
        return self._env_provider

    def _build_settings_handler(self) -> Any:
        if self._settings_handler_factory is not None:
            return self._settings_handler_factory()
        from ui.handlers.settings_handler import SettingsHandler

        return SettingsHandler()

    def persist(self, gateway_enabled: bool, backend: Optional[IRemoteGatewayBackend] = None) -> None:
        """Persists gateway_enabled in settings.ini, SettingsManager, .env, and runtime backend."""
        try:
            sh = self._build_settings_handler()
            sh.save_to_file({"gateway_enabled": gateway_enabled})
            if hasattr(sh, "_cached_settings") and sh._cached_settings is not None:
                sh._cached_settings.update({"gateway_enabled": gateway_enabled})

            try:
                sm = self._get_settings_manager()
                if sm:
                    curr = sm.load_settings()
                    curr["gateway_enabled"] = gateway_enabled
                    sm.save_settings(curr)
            except Exception:
                pass

            env_provider = self._get_env_provider()
            if env_provider:
                try:
                    env_provider.sync_variable("CARINA_GATEWAY_ENABLED", str(gateway_enabled))
                except Exception as env_err:
                    logger.debug(f"[RemoteGatewaySettingsPersister] Erro ao sincronizar .env: {env_err}")

            if backend is not None:
                backend.sync_enabled_state(gateway_enabled)

            logger.info(
                f"[RemoteGatewaySettingsPersister] Configurações persistidas com sucesso: enabled={gateway_enabled}"
            )
        except Exception as err:
            logger.error(f"[RemoteGatewaySettingsPersister] Falha ao persistir configurações: {err}", exc_info=True)
