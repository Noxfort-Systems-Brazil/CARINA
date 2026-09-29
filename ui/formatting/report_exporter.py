# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/formatting/report_exporter.py
# Author: Gabriel Moraes
# Date: September 2026

import base64
import logging
import os
import tempfile
from typing import Any, Optional

import flet as ft

from blocks.report_post_processor import ReportPostProcessor
from blocks.structured_report_builder import StructuredReportBuilder
from src.utils.settings_manager import SettingsManager
from ui.formatting.report_asset_resolver import ReportAssetResolver
from ui.formatting.report_config_builder import ReportConfigBuilder
from ui.handlers.locale_manager import LocaleManager


class ReportExporter:
    """
    Service handler that orchestrates configuration fetching, temporary image writing,
    and invocation of StructuredReportBuilder to export DOCX reports.
    Follows Clean Architecture Facade Pattern.
    """

    @staticmethod
    def export_report(
        page: ft.Page,
        locale_manager: LocaleManager,
        save_path: str,
        image_base64: str,
        text_content: str,
        results_dir: str,
        mode: str,  # "XAI", "MFD", or "PLANNING"
        agent_id: Optional[str] = None,
    ) -> bool:
        if not save_path.lower().endswith(".docx"):
            save_path += ".docx"

        tmp_img_path = None
        try:
            # 1. Resolve image asset and temp file (SRP)
            image_base64, tmp_img_path = ReportAssetResolver.resolve_image_file(results_dir, mode, image_base64)

            # 2. Build configuration dictionary and block order (SRP)
            settings = SettingsManager().load_settings()
            config, block_order = ReportConfigBuilder.build_config(settings, locale_manager, mode)

            def clean_str(val: Any) -> str:
                return "" if val is None else str(val).replace("|", "").strip()

            raw_scenario = os.path.basename(results_dir or "")
            if not raw_scenario or any(k in raw_scenario.lower() for k in ["hft", "live", "session"]):
                scenario_clean = "Sessão de Operação em Tempo Real"
            else:
                scenario_clean = raw_scenario.replace("_", " ").title()

            # Optional multi-agent XAI generation
            if mode == "XAI" and results_dir:
                try:
                    from xai.xai_report_generator import XaiReportGenerator

                    xai_gen = XaiReportGenerator(results_dir)
                    full_res = xai_gen.generate_full_multi_agent_report(primary_agent_id=agent_id)
                    if full_res:
                        if full_res.get("text_content"):
                            text_content = full_res["text_content"]
                        if full_res.get("image_base64"):
                            image_base64 = full_res["image_base64"]
                            ReportAssetResolver.cleanup_temp_file(tmp_img_path)
                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                                tmp_img.write(base64.b64decode(image_base64))
                                tmp_img_path = tmp_img.name
                except Exception as e:
                    logging.warning(f"[ReportExporter] Failed multi-agent XAI report generation: {e}")

            cleaned_text_content = (
                ReportPostProcessor.enforce_semantic_consistency(text_content) if text_content else ""
            )

            # Exclude standalone chart block if markdown already embeds inline figures
            if mode == "XAI" and cleaned_text_content and "![" in cleaned_text_content:
                block_order = [b for b in block_order if b.lower() != "chart"]

            engine_str = (
                "CARINA v1.0 (MFD Engine)"
                if mode == "MFD"
                else ("CARINA v1.0 (SAS Engine)" if mode == "PLANNING" else "CARINA v1.0 (XAI Engine)")
            )

            context = {
                "scenario": clean_str(scenario_clean),
                "engine_version": engine_str,
                "image_path": tmp_img_path,
                "text_content": cleaned_text_content,
                "results_dir": results_dir,
            }
            if agent_id is not None:
                context["agent_id"] = clean_str(agent_id)

            if mode == "PLANNING":
                lbl_scenario = locale_manager.get_string(
                    "structured_report.planning_label_scenario", default="Cenário de Operação:"
                )
                lbl_engine = locale_manager.get_string(
                    "structured_report.planning_label_engine", default="Motor Analítico SAS:"
                )
                context["metadata_rows"] = [
                    (clean_str(lbl_scenario), clean_str(context.get("scenario", "N/A"))),
                    (clean_str(lbl_engine), clean_str(context.get("engine_version", "CARINA v1.0.0"))),
                ]
            elif mode == "MFD":
                lbl_scenario = locale_manager.get_string(
                    "structured_report.mfd_label_scenario", default="Cenário de Operação:"
                )
                lbl_engine = locale_manager.get_string("structured_report.mfd_label_engine", default="Motor Analítico:")
                context["metadata_rows"] = [
                    (clean_str(lbl_scenario), clean_str(context.get("scenario", "N/A"))),
                    (clean_str(lbl_engine), clean_str(context.get("engine_version", "CARINA v1.0 (MFD Engine)"))),
                ]

            # Generate Report Document
            builder = StructuredReportBuilder(block_order=block_order)
            success = builder.generate_report(save_path, context, config)

            if success:
                success_msg = locale_manager.get_string(
                    "xai_viewer.export_success", default="Laudo exportado com sucesso para: {path}", path=save_path
                )
                page.snack_bar = ft.SnackBar(content=ft.Text(success_msg))
                page.snack_bar.open = True
            else:
                error_msg = locale_manager.get_string(
                    "xai_viewer.export_error", default="Erro ao gerar o laudo técnico."
                )
                page.snack_bar = ft.SnackBar(content=ft.Text(error_msg))
                page.snack_bar.open = True
            page.update()
            return success

        except Exception as ex:
            catch_msg = locale_manager.get_string(
                "xai_viewer.export_catch_error", default="Erro ao exportar laudo: {error}", error=str(ex)
            )
            page.snack_bar = ft.SnackBar(content=ft.Text(catch_msg))
            page.snack_bar.open = True
            page.update()
            return False
        finally:
            ReportAssetResolver.cleanup_temp_file(tmp_img_path)
