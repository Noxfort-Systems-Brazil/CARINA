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

# File: src/xai/report_text_section_renderer.py
# Author: Gabriel Moraes
# Date: August 14, 2026

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
