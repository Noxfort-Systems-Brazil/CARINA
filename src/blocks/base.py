# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict

try:
    from docx.shared import Pt, RGBColor
except ImportError:
    pass


class ReportBlock:
    """Base class for all modular report blocks."""

    def build(self, doc: Any, context: Dict[str, Any], config: Dict[str, Any]) -> None:
        raise NotImplementedError("Subclasses must implement build().")


def get_translated(config: Dict[str, Any], key: str, default: str) -> str:
    lm = config.get("locale_manager")
    if lm:
        return lm.get_string(key, default=default)
    return default


def add_markdown_paragraph(
    doc: Any,
    text: str,
    style: Any = None,
    font_size: float = None,
    bold: bool = False,
    space_before: float = None,
    first_line_indent: float = None,
) -> Any:
    p = doc.add_paragraph(style=style)
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if first_line_indent is not None:
        try:
            from docx.shared import Cm

            p.paragraph_format.first_line_indent = Cm(first_line_indent)
        except Exception:
            pass

    parts = text.split("**")
    is_bold = False
    for part in parts:
        if part:
            run = p.add_run(part)
            if is_bold or bold:
                run.bold = True
            if font_size is not None:
                run.font.size = Pt(font_size)
            try:
                run.font.color.rgb = RGBColor(0, 0, 0)
            except Exception:
                pass
        is_bold = not is_bold
    return p
