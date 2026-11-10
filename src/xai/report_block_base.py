# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
