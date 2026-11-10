# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import gc
import logging
from typing import Any

from slm.local_llama_transducer import LocalLlamaTransducer


class ReportTransducerFactory:
    """
    Factory for initializing, providing, and releasing neural transducer models used
    in technical report generation.
    """

    @staticmethod
    def create_transducer() -> Any:
        """
        Attempts to load the primary SemanticTransducer neural model.
        Falls back to LocalLlamaTransducer if initialization fails.

        Returns:
            Any: An initialized transducer instance exposing the generate_report interface.
        """
        try:
            from slm.semantic_transducer import SemanticTransducer

            transducer = SemanticTransducer()
            transducer.load_resources()
            logging.info("[REPORT_TRANSDUCER_FACTORY] SemanticTransducer (SLM) loaded successfully.")
            return transducer
        except Exception as e:
            logging.warning(
                f"[REPORT_TRANSDUCER_FACTORY] SemanticTransducer initialization failed: {e}. "
                "Falling back to LocalLlamaTransducer.",
                exc_info=True,
            )
            return LocalLlamaTransducer()

    @staticmethod
    def release_transducer(transducer: Any) -> None:
        """
        Safely deletes references to the transducer model and triggers explicit garbage collection.

        Args:
            transducer (Any): Transducer instance to be released.
        """
        if transducer is not None:
            try:
                del transducer
            except Exception as e:
                logging.debug(f"[REPORT_TRANSDUCER_FACTORY] Failed to delete transducer reference: {e}")

        gc.collect()
        logging.debug("[REPORT_TRANSDUCER_FACTORY] Transducer resources released and gc.collect() executed.")
