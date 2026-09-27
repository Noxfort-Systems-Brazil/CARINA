# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/formatting/report_asset_resolver.py
# Author: Gabriel Moraes
# Date: September 2026

import base64
import logging
import os
import tempfile
from typing import Optional, Tuple


class ReportAssetResolver:
    """
    Locates, decodes, and caches report chart images and temporary files.
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def resolve_image_file(
        results_dir: Optional[str], mode: str, image_base64: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Locates chart image on disk or decodes base64 string to a temporary file.
        Returns: (final_image_base64, tmp_img_path)
        """
        resolved_b64 = image_base64
        tmp_img_path = None

        if (not resolved_b64 or resolved_b64.strip() == "") and results_dir:
            if mode == "PLANNING":
                possible_paths = [
                    os.path.join(results_dir, "map_planning.png"),
                    os.path.join(results_dir, "maps", "map_planning.png"),
                ]
            elif mode == "MFD":
                possible_paths = [
                    os.path.join(results_dir, "mfd_curve.png"),
                    os.path.join(results_dir, "plots", "mfd_curve.png"),
                ]
            else:
                possible_paths = [
                    os.path.join(results_dir, "xai_importance.png"),
                    os.path.join(results_dir, "plots", "xai_importance.png"),
                ]
            for p in possible_paths:
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    try:
                        with open(p, "rb") as img_f:
                            resolved_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                        break
                    except Exception as e:
                        logging.warning(f"[ReportAssetResolver] Failed to read fallback image {p}: {e}")

        if resolved_b64 and resolved_b64.strip() != "":
            try:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                    tmp_img.write(base64.b64decode(resolved_b64))
                    tmp_img_path = tmp_img.name
            except Exception as e:
                logging.warning(f"[ReportAssetResolver] Failed to create temp image file: {e}")

        return resolved_b64, tmp_img_path

    @staticmethod
    def cleanup_temp_file(tmp_path: Optional[str]) -> None:
        """Safely removes a temporary file if it exists."""
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
