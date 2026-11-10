# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportTextSectionRenderer(ReportBlockBase):
    """
    Renders standard narrative text sections with titles and paragraph content.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Renders title and narrative paragraphs for standard report sections."""
        agent_ids = context.get("agent_ids", [])
        total_agents = len(agent_ids)

        title_key = block.get("title_key", "")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        for c_key in block.get("content_keys", []):
            content = self._t(c_key, total_agents=total_agents)
            if content:
                lines.append(content)

        lines.append("")
