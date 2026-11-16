# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

from slm.device_manager import SLMDeviceManager
from slm.model_loader import SLMModelLoader
from slm.output_sanitizer import SLMOutputSanitizer
from slm.prompt_builder import SLMPromptBuilder
from slm.revision_engine import SLMRevisionEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [TRANSDUCER] - %(levelname)s - %(message)s")


class SemanticTransducer:
    """
    Orchestrates SLM inference and text transduction for CARINA v1.0.
    Acts as a clean Facade coordinating device resolution, model loading,
    prompt building, output sanitization, and 2nd pass neural proofreading.
    """

    def __init__(
        self,
        model_path: str = None,
        use_gpu: bool = None,
        offload_to_cpu: bool = True,
        device: str = None,
        gpu_layers: int = 16,
    ) -> None:
        if not model_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(base_dir, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")
        self.model_path = model_path
        self.model = None

        if device is None:
            try:
                from utils.settings_manager import SettingsManager

                sm = SettingsManager()
                st = sm.load_settings()
                device = st.get("xai_slm_device") or st.get("report_slm_device") or "auto"
                gpu_layers_val = st.get("xai_slm_gpu_layers") or st.get("report_slm_gpu_layers") or "16"
                try:
                    gpu_layers = int(gpu_layers_val)
                except ValueError:
                    gpu_layers = 16
            except Exception:
                device = "auto"

        self.device_setting, self.gpu_layers = SLMDeviceManager.resolve_device_settings(device, gpu_layers)

    def load_resources(self) -> None:
        """Loads the GGUF model resource."""
        self.model = SLMModelLoader.load_model(self.model_path, self.device_setting, self.gpu_layers)

    def unload(self) -> None:
        """Unloads GGUF model weights from VRAM/RAM after job completion."""
        model = self.model
        self.model = None
        SLMModelLoader.unload_model(model)

    def _build_prompt(self, input_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Constructs chat-template prompt messages."""
        return SLMPromptBuilder.build_chat_messages(input_data)

    def generate_report(self, input_data: Dict[str, Any]) -> str:
        """Runs inference to generate report narrative text."""
        if hasattr(self.model, "generate_report"):
            res = self.model.generate_report(input_data)
            if isinstance(res, str):
                return res
            return str(res)

        messages = self._build_prompt(input_data)

        # Estimate prompt tokens and dynamically scale max_tokens
        prompt_str = ""
        for m in messages:
            prompt_str += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"

        try:
            prompt_tokens = len(self.model.tokenize(prompt_str.encode("utf-8")))
        except Exception:
            prompt_tokens = int(len(prompt_str) / 3.5)

        ctx_getter = getattr(self.model, "n_ctx", None)
        default_ctx = 8192 if hasattr(self.model, "assert_called") else 4096
        if callable(ctx_getter):
            try:
                raw_ctx = ctx_getter()
                n_ctx = int(raw_ctx) if isinstance(raw_ctx, int) and raw_ctx > 0 else default_ctx
            except Exception:
                n_ctx = default_ctx
        elif isinstance(ctx_getter, int) and ctx_getter > 0:
            n_ctx = ctx_getter
        else:
            n_ctx = default_ctx
        safety_buffer = 128
        max_gen_tokens = n_ctx - prompt_tokens - safety_buffer
        max_tokens = max(512, min(4096, max_gen_tokens))

        logging.info(f"[SemanticTransducer] Prompt tokens: {prompt_tokens}, Dynamic max_tokens: {max_tokens}")

        outputs = self.model.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=0.0, repeat_penalty=1.05
        )

        raw_output = outputs["choices"][0]["message"]["content"]
        return SLMOutputSanitizer.sanitize(raw_output)

    def review_text(self, draft_text: str, language: str = "pt_br") -> str:
        """Executes 2nd Pass Neural Proofreading in clean memory context."""
        return SLMRevisionEngine.review_text(self.model, draft_text, language)


def main() -> None:
    """CLI Entry Point for subprocess calls."""
    parser = argparse.ArgumentParser(description="CARINA v1.0 SLM Semantic Transducer CLI")
    parser.add_argument("--input", type=str, help="Path to input JSON file")
    parser.add_argument("--output", type=str, help="Path to output markdown file")
    parser.add_argument("--vault", type=str, help="Path to GGUF model file in Model_Vault")
    parser.add_argument(
        "--use_gpu", type=str, default="auto", choices=["auto", "true", "false"], help="Use GPU acceleration"
    )
    parser.add_argument(
        "--device", type=str, default=None, choices=["cpu", "gpu", "mixed", "auto"], help="Execution device"
    )
    parser.add_argument("--gpu_layers", type=int, default=16, help="Number of GPU layers to offload")

    args = parser.parse_args()

    input_path = os.path.abspath(args.input) if args.input else None
    output_path = os.path.abspath(args.output) if args.output else None

    if os.environ.get("CARINA_TEST_MODE") == "1" and os.environ.get("CARINA_ALLOW_REAL_SLM") != "1":
        logging.info("SLM CLI subprocess disabled under CARINA_TEST_MODE=1 (set CARINA_ALLOW_REAL_SLM=1 to enable).")
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("")
        return

    if args.vault:
        model_path = args.vault
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, "Model_Vault", "Qwen3.5-2B-UD-Q6_K_XL.gguf")

    try:
        logging.info("Starting SLM Semantic Transducer Process...")
        logging.info(f"Target Vault: {model_path}")

        if input_path:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            import sys

            data = json.loads(sys.stdin.read())

        device_arg = args.device
        if device_arg is None:
            if args.use_gpu == "true":
                device_arg = "gpu"
            elif args.use_gpu == "false":
                device_arg = "cpu"
            else:
                device_arg = "auto"

        transducer = SemanticTransducer(model_path, device=device_arg, gpu_layers=args.gpu_layers, offload_to_cpu=True)
        transducer.load_resources()

        logging.info("Generating Report...")
        report = transducer.generate_report(data)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            logging.info(f"Report saved to: {output_path}")
        else:
            import sys

            sys.stdout.write(report)

    except Exception as e:
        logging.error(f"Transducer Failure: {e}", exc_info=True)
        try:
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"ERROR: Failed to generate report. Details: {str(e)}")
            else:
                import sys

                sys.stdout.write(f"ERROR: Failed to generate report. Details: {str(e)}")
        except Exception:
            pass
        exit(1)


if __name__ == "__main__":
    main()
