# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from analysis.text_report_formatter import TextReportFormatter


class TextReportGenerator:
    """Formats analysis results into a professional text report."""

    def __init__(
        self,
        analysis_results: Dict[str, Any],
        analysis_params: Dict[str, Any],
        scenario_name: str,
        locale_manager: "LocaleManagerBackend",
    ):
        self.results = analysis_results
        self.params = analysis_params
        self.scenario_name = scenario_name
        self.locale_manager = locale_manager

    def generate_txt_report(self) -> str:
        """Delegates the complete report formatting to TextReportFormatter."""
        return TextReportFormatter.format_txt_report(
            results=self.results,
            params=self.params,
            scenario_name=self.scenario_name,
            locale_manager=self.locale_manager,
        )
