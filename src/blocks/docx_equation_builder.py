# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/blocks/docx_equation_builder.py
# Author: Gabriel Moraes
# Date: September 2026

import re
from typing import Any

try:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt
except ImportError:
    pass

from blocks.docx_text_builder import add_formatted_text_to_paragraph, add_omml_equation_to_document
from blocks.math_cleaner import clean_latex_math


class DocxEquationBuilder:
    """
    Renders centralized equations with ABNT NBR 14724 right-aligned tags into python-docx.
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def render_equation(doc: Any, line_str: str, default_font_size: float = 11.0, font_name: str = "Arial") -> bool:
        """
        Parses equation string wrapped in $$ and renders it using native OMML or formatted text.
        Returns True if line was processed as an equation, False otherwise.
        """
        if not (line_str.startswith("$$") and line_str.endswith("$$")):
            return False

        eq_raw = line_str[2:-2].strip()

        tag_match = re.search(r"\\tag\{(\d+)\}", eq_raw) or re.search(r"\s*\((\d+)\)\s*$", eq_raw)
        tag_str = ""
        if tag_match:
            tag_num = tag_match.group(1)
            tag_str = f"({tag_num})"
            eq_raw = re.sub(r"\\tag\{(\d+)\}", "", eq_raw)
            eq_raw = re.sub(r"\s*\(\d+\)\s*$", "", eq_raw).strip()

        # Try native Word OMML fraction rendering first
        if not add_omml_equation_to_document(doc, eq_raw, tag_str, font_name=font_name, font_size=default_font_size):
            cleaned_eq = clean_latex_math(eq_raw)
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(8)

            if tag_str:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                add_formatted_text_to_paragraph(
                    p, f"      **{cleaned_eq}**", font_size=default_font_size, font_name=font_name
                )
                r_tag = p.add_run(f"\t\t{tag_str}")
                r_tag.bold = True
                r_tag.font.name = font_name
                r_tag.font.size = Pt(default_font_size)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_formatted_text_to_paragraph(
                    p, f"**{cleaned_eq}**", font_size=default_font_size, font_name=font_name
                )

        return True
