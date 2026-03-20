import pytest
import time
from src.watchdog import Watchdog

@pytest.fixture
def watchdog_instance():
    """
    Cria uma instancia isolada do Watchdog (Safety).
    """
    # Criamos a instancia definindo 500ms de timeout
    wd = Watchdog(timeout_ms=500)
    return wd

@pytest.mark.unit
def test_watchdog_healthy_pulse(watchdog_instance):
    """
    Testa se o envio de pulsos constantes impede o gatilho de seguranca.
    """
    wd = watchdog_instance
    
    # Registra o heartbeat manual (simulando Synapse)
    wd.register_heartbeat()
    time.sleep(0.1)
    
    # Verifica a saude do sistema
    is_healthy = wd.check_system_health()
    
    assert is_healthy is True
    assert wd.is_in_failsafe is False

@pytest.mark.unit
def test_watchdog_timeout_trigger(watchdog_instance):
    """
    Simula um delay maior que o timeout_ms e verifica se o failsafe e ativado.
    """
    wd = watchdog_instance
    
    # Registra heartbeat base e defasa artificialmente
    wd.register_heartbeat()
    wd._last_heartbeat_time = time.perf_counter() - 0.6  # Defasagem de 600ms
    
    # A verificacao deve retornar False e ativar o Failsafe
    is_healthy = wd.check_system_health()
    
    assert is_healthy is False
    assert wd.is_in_failsafe is True

@pytest.mark.unit
def test_watchdog_recovery(watchdog_instance):
    """
    Testa se o Watchdog consegue se recuperar apos entrar em Failsafe.
    """
    wd = watchdog_instance
    wd._last_heartbeat_time = time.perf_counter() - 0.6
    wd.check_system_health()
    assert wd.is_in_failsafe is True
    
    # Novo heartbeat deve resetar o sistema
    wd.register_heartbeat()
    assert wd.is_in_failsafe is False
