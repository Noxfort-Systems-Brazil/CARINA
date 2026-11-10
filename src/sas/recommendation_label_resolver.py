# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from sas.template_repository import TemplateRepository


class RecommendationLabelResolver:
    """
    Responsibility (SRP & OCP): Resolves localized display labels for intersection recommendations
    (OPTIMIZE, ADD, REMOVE, MAINTAIN, UNSIGNALIZED) and signalized status flags.
    Follows SOLID principles.
    """

    @classmethod
    def get_recommendation_labels(
        cls, is_add: bool, is_remove: bool, is_keep: bool, is_no_signal: bool, language: str, is_optimize: bool = False
    ) -> str:
        """
        Resolves the localized string label for a traffic engineering recommendation.

        :param is_add: True if recommendation is ADD TRAFFIC LIGHT
        :param is_remove: True if recommendation is REMOVE TRAFFIC LIGHT
        :param is_keep: True if recommendation is MAINTAIN TRAFFIC LIGHT
        :param is_no_signal: True if recommendation is MAINTAIN UNSIGNALIZED
        :param language: Target language code
        :param is_optimize: True if recommendation is OPTIMIZE TRAFFIC LIGHT
        :return: Localized recommendation label string
        """
        templates = TemplateRepository.load_templates()
        lang_key = (language or "pt_br").lower()
        rec_dict = templates.get("recommendations", {}).get(
            lang_key, templates.get("recommendations", {}).get("pt_br", {})
        )

        if is_optimize:
            return rec_dict.get("optimize", "OTIMIZAR SEMÁFORO")
        elif is_add:
            return rec_dict.get("add", "ADICIONAR SEMÁFORO")
        elif is_remove:
            return rec_dict.get("remove", "REMOVER SEMÁFORO")
        elif is_no_signal:
            return rec_dict.get("no_signal", "MANTER NÃO SINALIZADO")
        return rec_dict.get("keep", "MANTER SEMÁFORO")

    @classmethod
    def get_status_label(cls, status_raw: str, language: str) -> str:
        """
        Resolves the localized status label string (Signalized / Unsignalized).

        :param status_raw: Raw status string from simulation topology
        :param language: Target language code
        :return: Localized status label string
        """
        templates = TemplateRepository.load_templates()
        lang_key = (language or "pt_br").lower()
        status_dict = templates.get("status", {}).get(lang_key, templates.get("status", {}).get("pt_br", {}))

        status_str_lower = str(status_raw or "").lower()
        is_active = any(x in status_str_lower for x in ["sinalizado", "active", "yes", "true", "1"]) and not any(
            x in status_str_lower for x in ["não", "nao", "un", "no_signal"]
        )

        if is_active:
            return status_dict.get("active", "Sinalizado")
        return status_dict.get("inactive", "Não Sinalizado")
