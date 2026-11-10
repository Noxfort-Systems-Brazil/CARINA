# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from typing import Any

from blocks.report_post_processor import ReportPostProcessor


class MFDNeuralProofreader:
    """
    Responsibility (SRP): Execute global 2nd pass neural proofreading on narrative report sections
    using the SLM Transducer, enforcing safety boundaries and clean fallback error handling.
    """

    @staticmethod
    def proofread_narrative(
        narrative_text: str, raw_exec_summary: str = "", transducer: Any = None, lang: str = "pt_br"
    ) -> str:
        """
        Executes a single global proofreading pass over narrative sections 1 through 5.

        :param narrative_text: Input narrative Markdown text
        :param raw_exec_summary: Raw executive summary string to check bypass conditions
        :param transducer: SLM transducer instance
        :param lang: UI target language
        :return: Proofread narrative Markdown text string
        """
        if not narrative_text or len(narrative_text.strip()) < 10:
            return narrative_text

        # Bypass proofreading pass if transducer is missing or does not have review_text method
        if transducer is None or not hasattr(transducer, "review_text"):
            return narrative_text

        try:
            logging.info(
                "[MFD_NEURAL_PROOFREADER] Executing single global proofreading pass on narrative sections 1-5..."
            )
            revised_text = transducer.review_text(narrative_text, language=lang)
            if revised_text and len(revised_text.strip()) > len(narrative_text) * 0.4:
                logging.info("[MFD_NEURAL_PROOFREADER] Global proofreading pass completed successfully.")
                narrative_text = revised_text
            else:
                logging.warning(
                    "[MFD_NEURAL_PROOFREADER] Proofreading returned truncated output; retaining original draft."
                )
        except Exception as rev_err:
            logging.warning(f"[MFD_NEURAL_PROOFREADER] Single global proofreading pass failed: {rev_err}", exc_info=True)

        narrative_text = ReportPostProcessor.enforce_semantic_consistency(narrative_text)
        narrative_text = ReportPostProcessor.sanitize_truncated_text(narrative_text)
        return narrative_text
