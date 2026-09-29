# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: src/xai/report_block_base.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from utils.locale_manager_backend import LocaleManagerBackend


class ReportBlockBase(ABC):
    """
    Abstract base class for modular XAI Markdown report block renderers.
    Follows Single Responsibility and Interface Segregation principles.
    """

    def __init__(self, templates: Dict[str, Any], locale_manager: Optional[LocaleManagerBackend] = None) -> None:
        self.templates = templates
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()

    def _t(self, key: str, default: str = "", **kwargs) -> str:
        """Helper to resolve localized string templates."""
        tmpl = self.templates.get(key, default)
        if kwargs and tmpl:
            try:
                return tmpl.format(**kwargs)
            except Exception:
                return tmpl
        return tmpl

    @abstractmethod
    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Renders a specific layout block into the lines buffer.
        :param lines: Target list of strings accumulating Markdown output.
        :param block: Layout configuration block descriptor.
        :param context: Unified execution and analytical data context dictionary.
        """
        pass
