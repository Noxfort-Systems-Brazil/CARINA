# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/sas/docx_report_assembler.py
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from src.sas.docx_report_assembler import DocxReportAssembler


class TestDocxReportAssembler:
    def test_assemble_docx_to_path_mfd_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_docx = os.path.join(tmp_dir, "output.docx")
            scenario_dir = os.path.join(tmp_dir, "scenarios", "grid4x4")
            os.makedirs(scenario_dir, exist_ok=True)

            with (
                patch("src.sas.report_template_provider.ReportTemplateProvider.get_layout_translations", return_value={}),
                patch("src.utils.settings_manager.SettingsManager.load_settings", return_value={"report_font_size": "12.0"}),
                patch("src.blocks.structured_report_builder.StructuredReportBuilder") as mock_builder_cls,
            ):
                mock_builder = MagicMock()
                mock_builder.generate_report.return_value = True
                mock_builder_cls.return_value = mock_builder

                res = DocxReportAssembler.assemble_docx_to_path(
                    target_path=target_docx,
                    scenario_dir=scenario_dir,
                    report_text="# Relatório MFD\nConteúdo técnico.",
                    ui_language="pt_br",
                    mode="MFD",
                )

                assert res == target_docx
                assert mock_builder.generate_report.called
                args, kwargs = mock_builder.generate_report.call_args
                context = args[1]
                config = args[2]
                assert config["mode"] == "MFD"
                assert "LAUDO TÉCNICO DE DESEMPENHO" in config["title"]
                assert context["scenario"] == "Grid4X4"

    def test_assemble_docx_to_path_xai_and_settings_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_docx = os.path.join(tmp_dir, "xai_output.docx")
            scenario_dir = os.path.join(tmp_dir, "hft_live_session")
            os.makedirs(scenario_dir, exist_ok=True)

            with (
                patch("src.sas.report_template_provider.ReportTemplateProvider.get_layout_translations", return_value={"main_title": "LAUDO XAI"}),
                patch("src.utils.settings_manager.SettingsManager.load_settings", side_effect=ValueError("Corrupt ini")),
                patch("src.blocks.structured_report_builder.StructuredReportBuilder") as mock_builder_cls,
            ):
                mock_builder = MagicMock()
                mock_builder.generate_report.return_value = True
                mock_builder_cls.return_value = mock_builder

                res = DocxReportAssembler.assemble_docx_to_path(
                    target_path=target_docx,
                    scenario_dir=scenario_dir,
                    report_text="# XAI Report",
                    ui_language="en",
                    mode="XAI",
                )

                assert res == target_docx
                args = mock_builder.generate_report.call_args[0]
                context = args[1]
                assert context["scenario"] == "Sessão de Operação em Tempo Real"

    def test_assemble_docx_generation_failure_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_docx = os.path.join(tmp_dir, "fail.docx")
            with (
                patch("src.sas.report_template_provider.ReportTemplateProvider.get_layout_translations", return_value={}),
                patch("src.utils.settings_manager.SettingsManager.load_settings", return_value={}),
                patch("src.blocks.structured_report_builder.StructuredReportBuilder") as mock_builder_cls,
            ):
                mock_builder = MagicMock()
                mock_builder.generate_report.return_value = False
                mock_builder_cls.return_value = mock_builder

                with pytest.raises(RuntimeError, match="Failed to generate structured DOCX report"):
                    DocxReportAssembler.assemble_docx_to_path(
                        target_path=target_docx,
                        scenario_dir=tmp_dir,
                        report_text="fail",
                    )

    def test_assemble_docx_convenience_method(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(DocxReportAssembler, "assemble_docx_to_path", return_value="/tmp/done.docx") as mock_asm:
                out = DocxReportAssembler.assemble_docx(tmp_dir, "text", "pt_br")
                assert out == "/tmp/done.docx"
                expected_path = os.path.join(tmp_dir, "Laudo_Tecnico_Oficial.docx")
                mock_asm.assert_called_once_with(expected_path, tmp_dir, "text", "pt_br")
