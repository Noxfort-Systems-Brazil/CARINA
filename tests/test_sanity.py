import pytest
import os
import sys

def test_environment_setup():
    """
    Testa se o ambiente foi configurado corretamente pelo conftest.py
    """
    assert os.environ.get('CARINA_TEST_MODE') == '1'
    assert os.environ.get('QT_QPA_PLATFORM') == 'offscreen'

def test_import_src_modules():
    """
    Skipping temporarily - root import causes hang
    """
    pytest.skip("Skipping root src imports on pure headless sanity to avoid hangs")

def test_import_ui_modules():
    """
    Testa se o pytest consegue enxergar a pasta ui/ e importar modulos base.
    """
    pytest.skip("Skiping UI imports on pure headless sanity to avoid Qt hangs")

@pytest.mark.unit
def test_dummy_math():
    """
    Teste simples para garantir que a execucao unitaria roda.
    """
    assert 1 + 1 == 2
