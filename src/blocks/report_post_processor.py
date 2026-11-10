# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any

from blocks.report_number_formatter import ReportNumberFormatter
from blocks.report_semantic_cleaner import ReportSemanticCleaner
from blocks.report_text_sanitizer import ReportTextSanitizer


class ReportPostProcessor:
    """
    Responsibility (SRP): Global Facade for ABNT report post-processing, coordinating
    number formatting, LLM text sanitization, and semantic consistency cleaning.
    """

    @staticmethod
    def get_configured_distance_unit() -> str:
        return ReportNumberFormatter.get_configured_distance_unit()

    @staticmethod
    def get_configured_time_unit() -> str:
        return ReportNumberFormatter.get_configured_time_unit()

    @staticmethod
    def get_configured_decimal_separator() -> str:
        return ReportNumberFormatter.get_configured_decimal_separator()

    @staticmethod
    def get_configured_thousands_separator() -> str:
        return ReportNumberFormatter.get_configured_thousands_separator()

    @classmethod
    def format_number(cls, val: Any, decimal_places: int = 1) -> str:
        return ReportNumberFormatter.format_number(val, decimal_places=decimal_places)

    @classmethod
    def clean_ai_preamble(cls, text: str) -> str:
        return ReportTextSanitizer.clean_ai_preamble(text)

    @classmethod
    def format_executive_summary(cls, raw_summary: str, intervention_rate: float) -> str:
        return ReportTextSanitizer.format_executive_summary(raw_summary, intervention_rate)

    @staticmethod
    def deduplicate_justification_paragraphs(text: str) -> str:
        return ReportTextSanitizer.deduplicate_justification_paragraphs(text)

    @classmethod
    def sanitize_zero_maintenance_protocol(cls, text: str, keep_count: int) -> str:
        return ReportTextSanitizer.sanitize_zero_maintenance_protocol(text, keep_count)

    @staticmethod
    def sanitize_truncated_text(text: str) -> str:
        return ReportTextSanitizer.sanitize_truncated_text(text)

    @classmethod
    def enforce_semantic_consistency(cls, text: str, is_signalized: bool = True) -> str:
        return ReportSemanticCleaner.enforce_semantic_consistency(text, is_signalized=is_signalized)
