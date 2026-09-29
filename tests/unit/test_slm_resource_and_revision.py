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

# File: tests/unit/test_slm_resource_and_revision.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for SLM ResourceManager and SLMRevisionEngine

from unittest.mock import MagicMock, patch

import pytest

from slm.resource_manager import ResourceManager
from slm.revision_engine import SLMRevisionEngine


def test_resource_manager_initialization_and_accessors():
    """Tests ResourceManager initialization and default device assignment."""
    rm = ResourceManager(model_path="/fake/model/path", use_gpu=False)
    assert rm.get_device() == "cpu"
    assert rm.get_model() is None
    assert rm.get_tokenizer() is None


@patch("slm.resource_manager.AutoTokenizer.from_pretrained")
@patch("slm.resource_manager.AutoModelForCausalLM.from_pretrained")
def test_resource_manager_load_and_cleanup(mock_model_cls, mock_tok_cls):
    """Tests loading neural weights into memory and subsequent garbage cleanup."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    mock_model_cls.return_value = mock_model
    mock_tok_cls.return_value = mock_tokenizer

    rm = ResourceManager(model_path="/fake/model/path")
    success = rm.load_resources()
    assert success is True
    assert rm.get_model() == mock_model
    assert rm.get_tokenizer() == mock_tokenizer

    # Test moving to GPU without CUDA
    with patch("torch.cuda.is_available", return_value=False):
        assert rm.move_model_to_device("cuda") is False

    # Test moving to CPU
    assert rm.move_model_to_device("cpu") is True

    # Test resource cleanup
    rm.cleanup()
    assert rm.get_model() is None
    assert rm.get_tokenizer() is None


def test_slm_revision_engine_prompt_loader():
    """Tests multilingue prompt retrieval with default fallback."""
    pt_prompt = SLMRevisionEngine.load_revision_prompt("pt_br")
    en_prompt = SLMRevisionEngine.load_revision_prompt("en")
    es_prompt = SLMRevisionEngine.load_revision_prompt("es")

    assert isinstance(pt_prompt, str) and len(pt_prompt) > 0
    assert isinstance(en_prompt, str) and len(en_prompt) > 0
    assert isinstance(es_prompt, str) and len(es_prompt) > 0


def test_slm_revision_engine_short_text():
    """Tests that short texts bypass neural proofreading."""
    short = "Curto."
    result = SLMRevisionEngine.review_text(None, short)
    assert result == short


def test_slm_revision_engine_successful_proofreading():
    """Tests normal neural proofreading through mock chat completion."""
    mock_model = MagicMock()
    mock_model.tokenize.return_value = [1, 2, 3]
    mock_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "O fluxo de tráfego foi estabilizado perfeitamente."}}]
    }

    draft = "O fluxo de trafego foi estabilizado perfeitamente."
    revised = SLMRevisionEngine.review_text(mock_model, draft, language="pt_br")
    assert "estabilizado" in revised


def test_slm_revision_engine_hallucination_boundary_fallback():
    """Tests fallback to original text when hallucinations (e.g. Cruzamento A) are injected."""
    mock_model = MagicMock()
    mock_model.tokenize.return_value = [1, 2, 3]
    mock_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Dados inventados para o Cruzamento A na simulação."}}]
    }

    draft = "Relatório de desempenho da malha semafórica central durante o pico."
    fallback = SLMRevisionEngine.review_text(mock_model, draft, language="pt_br")
    assert fallback == draft.strip()
