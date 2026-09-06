# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: src/xai/report_equations_renderer.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportEquationsRenderer(ReportBlockBase):
    """
    Renders formal mathematical equations, parameters, and completeness axioms for XAI methodologies.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Renders mathematical equation blocks dynamically configured in layout."""
        title_key = block.get("title_key", "")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        intro_key = block.get("intro_key", "")
        if intro_key and self._t(intro_key):
            lines.append(self._t(intro_key))
            lines.append("")

        for eq in block.get("equations", []):
            formula = self._t(eq.get("formula_key", ""))
            if formula:
                t_key = eq.get("title_key")
                if t_key and self._t(t_key):
                    lines.append(self._t(t_key))

                d_key = eq.get("desc_key")
                if d_key and self._t(d_key):
                    lines.append(self._t(d_key))

                lines.append(formula)

                p_key = eq.get("params_key")
                if p_key and self._t(p_key):
                    lines.append(self._t(p_key))

                if eq.get("completeness_formula_key") and self._t(eq.get("completeness_formula_key")):
                    lines.append("")
                    ax_key = eq.get("completeness_axiom_key")
                    if ax_key and self._t(ax_key):
                        lines.append(self._t(ax_key))
                    lines.append(self._t(eq["completeness_formula_key"]))
                    cd_key = eq.get("completeness_desc_key")
                    if cd_key and self._t(cd_key):
                        lines.append(self._t(cd_key))

                lines.append("")
