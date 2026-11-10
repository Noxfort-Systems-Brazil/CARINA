# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import subprocess
import sys
from typing import Any, Dict


class MFDSubprocessFallback:
    """
    Responsibility (SRP): Run SLM transducer CLI in an isolated subprocess
    when mock or subprocess fallback is required for memory isolation.
    """

    @staticmethod
    def try_subprocess_transducer(payload: Dict[str, Any], device: str = "auto", gpu_layers: str = "16") -> str:
        """
        Executes isolated GGUF transducer inference in a separate process.

        :param payload: JSON payload dictionary for SLM inference
        :param device: Target compute device ("auto", "cpu", "cuda")
        :param gpu_layers: String specifying GPU layers to offload
        :return: Generated report text string
        """
        try:
            cmd = [sys.executable, "-m", "slm.semantic_transducer", "--device", device, "--gpu_layers", str(gpu_layers)]
            result = subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                stdout_text = (result.stdout or "").strip()
                if not stdout_text:
                    return ""
                try:
                    resp = json.loads(stdout_text)
                    if isinstance(resp, dict):
                        return resp.get("report_text", stdout_text)
                    return str(resp)
                except Exception:
                    return stdout_text
            else:
                logging.warning(f"[MFD_SUBPROCESS_FALLBACK] Isolated process error: {result.stderr}")
                return ""
        except Exception as e:
            logging.error(f"[MFD_SUBPROCESS_FALLBACK] Failed to execute isolated SLM transducer process: {e}", exc_info=True)
            return ""
