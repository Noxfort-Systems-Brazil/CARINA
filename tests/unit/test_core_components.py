import pytest
import os
import sys

def test_enums_maturity():
    """
    Testa se conseguimos carregar e utilizar os Enums core (Maturity)
    """
    try:
        from src.core.enums import Maturity
        assert Maturity.CHILD.name == 'CHILD'
        assert Maturity.ADULT.name == 'ADULT'
    except ImportError as e:
        pytest.fail(f"Falha ao carregar core enums: {e}")

def test_ai_process_function_exists():
    """
    Testa se a porta de entrada principal da IA (HFT) existe 
    (sem invoca-la para nao armar tensores).
    """
    try:
        from src.main import run_ai_process
        assert callable(run_ai_process), "run_ai_process deve ser invocavel"
    except ImportError as e:
        pytest.fail(f"Falha ao carregar main.py: {e}")

@pytest.mark.unit
def test_locale_backend():
    """
    Garante que o manipulador de idiomas pode ser inicializado sem colidir.
    """
    try:
        from src.utils.locale_manager_backend import LocaleManagerBackend
        lm = LocaleManagerBackend()
        # O padrao deveria ser pt_BR ou en_US, testando se n e vazio
        assert lm.current_lang_data is not None
        assert isinstance(lm.get_string("dummy.key", fallback="fallback_value"), str)
    except Exception as e:
        pytest.fail(f"Falha no Manger de Locales: {e}")
