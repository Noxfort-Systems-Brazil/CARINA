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

# File: src/blocks/docx_text_builder.py
# Author: Gabriel Moraes
# Date: August 9, 2026

from typing import Any

from src.blocks.docx_subscript_formatter import add_formatted_text_to_paragraph, add_text_run_with_subscript_support
from src.blocks.docx_template_loader import DocxTemplateLoader

# Re-exports for backward compatibility
__all__ = [
    "add_omml_equation_to_document",
    "add_formatted_text_to_paragraph",
    "add_text_run_with_subscript_support",
    "DocxTemplateLoader",
]


def add_omml_equation_to_document(
    doc: Any, eq_raw: str, tag_str: str = "", font_name: str = "Arial", font_size: float = 11.0
) -> bool:
    """
    Renders native Word OMML equations with stacked vertical fractions (horizontal bar)
    and right-aligned ABNT tag (1)-(4), dynamically driven by JSON configuration.
    """
    try:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import parse_xml
        from docx.shared import Pt
    except ImportError:
        return False

    omml_config = DocxTemplateLoader.load_omml_templates()
    ns_decl = omml_config.get(
        "namespaces",
        (
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        ),
    )
    templates = omml_config.get("templates", {})

    omml_xml = None

    # Try matching equation by exact formula or keyword signatures
    for eq_key, eq_data in templates.items():
        xml_template = eq_data.get("omml_xml", "")
        keywords = eq_data.get("keywords", [])
        if any(kw in eq_raw for kw in keywords):
            omml_xml = xml_template.replace("$$NAMESPACES$$", ns_decl)
            break

    # Fallback to direct pattern match if not matched by keywords
    if not omml_xml:
        if "α_{ij}" in eq_raw or "\\alpha_{ij}" in eq_raw or "ST-GATv2" in eq_raw or "LeakyReLU" in eq_raw:
            omml_xml = templates.get("eq2_gatv2", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "Atenção(Q, K, V)" in eq_raw or "softmax" in eq_raw:
            omml_xml = templates.get("eq3_cross_attention", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "Q(s, a)" in eq_raw or "D3QN" in eq_raw or "V(s)" in eq_raw:
            omml_xml = templates.get("eq4_d3qn", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "y(t)" in eq_raw or "PPO-TCN" in eq_raw:
            omml_xml = templates.get("eq1_tcn", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "PAE" in eq_raw or "\\mathcal{L}_{PAE}" in eq_raw or "Autoencoder" in eq_raw:
            omml_xml = templates.get("eq5_pae", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "GradientesIntegrados" in eq_raw or "IntegratedGradients" in eq_raw or "Captum" in eq_raw:
            omml_xml = templates.get("eq5_captum", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)
        elif "∑" in eq_raw and "GradientesIntegrados" in eq_raw:
            omml_xml = templates.get("eq6_completeness", {}).get("omml_xml", "").replace("$$NAMESPACES$$", ns_decl)

    if not omml_xml:
        return False

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if tag_str else WD_ALIGN_PARAGRAPH.CENTER

    omml_elem = parse_xml(omml_xml)
    p._element.append(omml_elem)

    if tag_str:
        r_tag = p.add_run(f"\t\t{tag_str}")
        r_tag.bold = True
        r_tag.font.name = font_name
        r_tag.font.size = Pt(font_size)

    return True
