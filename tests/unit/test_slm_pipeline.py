# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_slm_pipeline.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from slm.device_manager import SLMDeviceManager
from slm.model_loader import SLMModelLoader
from slm.prompt_builder import SLMPromptBuilder
from slm.revision_engine import SLMRevisionEngine
from slm.semantic_transducer import SemanticTransducer


@pytest.mark.unit
def test_device_manager_explicit():
    # CPU explicit
    dev, layers = SLMDeviceManager.resolve_device_settings("cpu", 10)
    assert dev == "cpu"
    assert layers == 0

    # GPU with CUDA mocked available
    with patch("torch.cuda.is_available", return_value=True):
        dev, layers = SLMDeviceManager.resolve_device_settings("gpu", 10)
        assert dev == "gpu"
        assert layers == -1

    # Mixed with CUDA available
    with patch("torch.cuda.is_available", return_value=True):
        dev, layers = SLMDeviceManager.resolve_device_settings("mixed", 8)
        assert dev == "mixed"
        assert layers == 8

    # GPU requested but CUDA unavailable -> CPU fallback
    with patch("torch.cuda.is_available", return_value=False):
        dev, layers = SLMDeviceManager.resolve_device_settings("gpu", 10)
        assert dev == "cpu"
        assert layers == 0


@pytest.mark.unit
def test_device_manager_auto_vram():
    # Auto: CUDA available with >= 3GB VRAM
    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.mem_get_info", return_value=(4 * (1024**3), 8 * (1024**3)), create=True),
    ):
        dev, layers = SLMDeviceManager.resolve_device_settings(None)
        assert dev == "gpu"
        assert layers == -1

    # Auto: CUDA available with < 3GB VRAM
    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.mem_get_info", return_value=(1 * (1024**3), 8 * (1024**3)), create=True),
    ):
        dev, layers = SLMDeviceManager.resolve_device_settings(None)
        assert dev == "cpu"
        assert layers == 0

    # Auto: CUDA unavailable
    with patch("torch.cuda.is_available", return_value=False):
        dev, layers = SLMDeviceManager.resolve_device_settings(None)
        assert dev == "cpu"
        assert layers == 0


@pytest.mark.unit
def test_prompt_builder():
    db = {
        "AUTO": {"pt_br": "Instrucao Auto PT", "en": "Auto instruction EN"},
        "MFD_OPTIMIZATION": {"pt_br": "Instrucao MFD"},
    }

    # Standard Auto
    payload = {"mode": "AUTO", "language": "pt_BR", "attributions": {"speed": 45.2}}
    msgs = SLMPromptBuilder.build_chat_messages(payload, prompts_db=db)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "Instrucao Auto PT" in msgs[0]["content"]
    assert "45.2" in msgs[1]["content"]

    # Sub-modes
    sub_modes = ["EXECUTIVE_SUMMARY", "CONCLUSIONS", "FINAL_TECHNICAL_OPINION", "SINGLE_INTERSECTION_AUDIT"]
    for sm in sub_modes:
        payload_sm = {"mode": "MFD_OPTIMIZATION", "sub_mode": sm, "attributions": {}}
        msgs_sm = SLMPromptBuilder.build_chat_messages(payload_sm, prompts_db=db)
        assert len(msgs_sm) == 2
        assert "Engenheiro de Tráfego" in msgs_sm[0]["content"]


@pytest.mark.unit
def test_model_loader_file_not_found():
    with pytest.raises(FileNotFoundError):
        SLMModelLoader.load_model("/non/existent/model.gguf", "cpu", 0)


@pytest.mark.unit
def test_model_loader_success():
    with patch("os.path.exists", return_value=True), patch.dict("sys.modules", {"llama_cpp": MagicMock()}):
        import llama_cpp

        mock_instance = MagicMock()
        llama_cpp.Llama.return_value = mock_instance

        # CPU load
        model = SLMModelLoader.load_model("dummy.gguf", "cpu", 0)
        assert model == mock_instance

        # GPU load fallback to CPU if GPU raises
        llama_cpp.Llama.side_effect = [RuntimeError("CUDA OOM"), mock_instance]
        model = SLMModelLoader.load_model("dummy.gguf", "gpu", -1)
        assert model == mock_instance


@pytest.mark.unit
def test_revision_engine():
    # Empty or short text returns unchanged
    assert SLMRevisionEngine.review_text(None, "short") == "short"

    mock_model = MagicMock()
    mock_model.tokenize.return_value = [1, 2, 3]

    # Normal revision
    mock_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Texto revisado perfeitamente sem erros gramaticais."}}]
    }
    draft = "Texto com erros que deve ser corrigido com perfeicao."
    res = SLMRevisionEngine.review_text(mock_model, draft)
    assert "Texto revisado" in res

    # Anti-hallucination check: hallucinated Cruzamento A falls back to draft
    mock_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Texto revisado | Cruzamento A | com dados falsos."}}]
    }
    res_hallucinated = SLMRevisionEngine.review_text(mock_model, draft)
    assert res_hallucinated == draft

    # Extreme length reduction falls back to draft
    mock_model.create_chat_completion.return_value = {"choices": [{"message": {"content": "Tiny"}}]}
    res_too_short = SLMRevisionEngine.review_text(mock_model, draft)
    assert res_too_short == draft


@pytest.mark.unit
def test_semantic_transducer_facade():
    with patch("slm.device_manager.SLMDeviceManager.resolve_device_settings", return_value=("cpu", 0)):
        transducer = SemanticTransducer(model_path="dummy.gguf", device="cpu", gpu_layers=0)
        assert transducer.device_setting == "cpu"

        # Mock model and inference
        mock_model = MagicMock(spec=["tokenize", "create_chat_completion"])
        mock_model.tokenize.return_value = [1, 2, 3]
        mock_model.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Relatorio de Transducao Gerado com Sucesso."}}]
        }
        transducer.model = mock_model

        report = transducer.generate_report({"mode": "AUTO", "attributions": {}})
        assert "Relatorio de Transducao Gerado" in report
