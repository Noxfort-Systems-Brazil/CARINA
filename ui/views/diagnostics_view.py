# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import glob
import logging
import os
import threading
import time

import flet as ft

from src.utils.paths import get_base_output_dir
from ui.handlers.locale_manager import LocaleManager
from ui.widgets.audit_log_widget import AuditLogWidget
from ui.widgets.mfd_viewer_widget import MfdViewerWidget
from ui.widgets.xai_viewer_widget import XaiViewerWidget


class DiagnosticsView(ft.Column):
    """
    View responsible for system diagnostics.

    UPDATE: Uses get_base_output_dir() to ensure UI
    looks at the same 'results' folder as the Backend.
    """

    def __init__(self, locale_manager: LocaleManager, control_client=None):
        super().__init__()
        self.locale_manager = locale_manager
        self.control_client = control_client
        self.expand = True

        # --- PATH CORRECTION ---
        # The backend uses get_base_output_dir(), so the UI should use it too.
        self.project_root = get_base_output_dir()

        self.results_dir = os.path.join(self.project_root, "results", "hft_live_session")

        logging.info(f"[UI_DIAG] DiagnosticsView inicializada.")
        logging.info(f"[UI_DIAG] Pasta de Resultados (Backend): {self.results_dir}")

        # Widgets
        self.mfd_viewer = MfdViewerWidget(
            locale_manager, results_dir=self.results_dir, control_client=self.control_client
        )

        # XAI Widget now receives the CORRECT directory
        self.xai_viewer = XaiViewerWidget(locale_manager, results_dir=self.results_dir)
        self.audit_viewer = AuditLogWidget(locale_manager)

        # Control
        self.watching = False
        self.watch_thread = None

        # Layout
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text=locale_manager.get_string("diagnostics_view.nav_mfd", default="MFD Optimization Analysis"),
                    icon=ft.Icons.AUTO_GRAPH_ROUNDED,
                    content=ft.Container(content=self.mfd_viewer, padding=10),
                ),
                ft.Tab(
                    text=locale_manager.get_string("diagnostics_view.nav_xai", default="Neural Analysis (XAI)"),
                    icon=ft.Icons.PSYCHOLOGY_ROUNDED,
                    content=ft.Container(content=self.xai_viewer, padding=10),
                ),
                ft.Tab(
                    text=locale_manager.get_string("diagnostics_view.nav_audit", default="Auditoria (Audit Logs)"),
                    icon=ft.Icons.POLICY_ROUNDED,
                    content=ft.Container(content=self.audit_viewer, padding=10),
                ),
            ],
            expand=True,
        )

        self.controls = [self.tabs]

    def did_mount(self):
        logging.info("[UI_DIAG] View montada. Iniciando Agent Watcher...")
        self.start_log_watcher()

    def will_unmount(self):
        logging.info("[UI_DIAG] View desmontando. Parando Agent Watcher...")
        self.stop_log_watcher()

    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        self.tabs.tabs[0].text = locale_manager.get_string(
            "diagnostics_view.nav_mfd", default="MFD Optimization Analysis"
        )
        self.tabs.tabs[1].text = locale_manager.get_string("diagnostics_view.nav_xai", default="Neural Analysis (XAI)")
        self.tabs.tabs[2].text = locale_manager.get_string(
            "diagnostics_view.nav_audit", default="Auditoria (Audit Logs)"
        )
        self.mfd_viewer.update_translations(locale_manager)
        self.xai_viewer.update_translations(locale_manager)
        if hasattr(self.audit_viewer, "update_translations"):
            self.audit_viewer.update_translations(locale_manager)
        if self.page:
            self.update()

    def start_log_watcher(self):
        if not self.watching:
            self.watching = True
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()

    def stop_log_watcher(self):
        self.watching = False

    def _watch_loop(self):
        """Monitors ONLY the Log file and the Agent list."""
        last_log_size = 0
        last_agent_ids = []

        while self.watching:
            try:
                if not self.page:
                    time.sleep(1.0)
                    continue

                # --- 1. Agent Discovery (Agent List) ---
                checkpoints_dir = os.path.join(self.results_dir, "checkpoints")
                if os.path.exists(checkpoints_dir):
                    agent_files = glob.glob(os.path.join(checkpoints_dir, "agent_*.pth"))
                    agent_ids = sorted(
                        [os.path.basename(f).replace("agent_", "").replace(".pth", "") for f in agent_files]
                    )
                    if agent_ids and agent_ids != last_agent_ids:
                        last_agent_ids = agent_ids
                        self.xai_viewer.update_agent_list(agent_ids)

            except Exception as e:
                err_str = str(e)
                if "Event loop is closed" in err_str or "cannot schedule new futures" in err_str:
                    break
                logging.error(f"[UI_DIAG] Erro no loop de logs: {e}", exc_info=True)
                time.sleep(2.0)

            time.sleep(1.0)
