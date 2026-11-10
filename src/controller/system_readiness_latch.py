# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging


class SystemReadinessLatch:
    """
    Manages the two-stage readiness process (UI and Backend).
    Unlocks the AI engine for decision making when both are ready.
    """

    def __init__(self, traffic_frame_processor, locale_manager=None):
        self.traffic_frame_processor = traffic_frame_processor
        self.locale_manager = locale_manager
        self.is_ui_ready = True
        self.is_backend_ready = True
        self.check_system_readiness()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def set_ui_ready(self):
        self.is_ui_ready = True
        self.check_system_readiness()

    def set_backend_ready(self):
        self.is_backend_ready = True
        self.check_system_readiness()

    def check_system_readiness(self):
        if self.is_ui_ready and self.is_backend_ready:
            logging.info(
                self._get_string(
                    "controller.latch.unlocked",
                    default="✅ [LATCH] Front-end and API fully loaded. Unlocking AI Engine for decision making.",
                )
            )
            self.traffic_frame_processor.set_system_ready(True)
        else:
            if not self.is_ui_ready:
                logging.warning(
                    self._get_string(
                        "controller.latch.waiting_ui",
                        default="⚠️ [LATCH] AI Engine paused: waiting for Front-End (UI) readiness ('carina_ready'). Frames will be dropped.",
                    )
                )
            if not self.is_backend_ready:
                logging.warning(
                    self._get_string(
                        "controller.latch.waiting_backend",
                        default="⚠️ [LATCH] AI Engine paused: waiting for Backend components to finish loading.",
                    )
                )
