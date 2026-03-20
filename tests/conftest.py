import os
import sys
import pytest

# Ensure we're running from CARINA_CORE root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCK HEAVY IMPORTS BEFORE THEY HAPPEN ---
# Isso impede que o PyTorch, OpenCV, ou PyQt tentem iniciar contextos pesados 
# (como CUDA ou X11) apenas porque um arquivo os importou no topo.
class DummyTorch:
    class cuda:
        @staticmethod
        def is_available(): return False
        @staticmethod
        def get_device_name(idx): return 'Mock CPU'
    class nn:
        class Module: pass
    class Tensor: pass
    
    @staticmethod
    def device(name): return name
    
    @staticmethod
    def no_grad():
        class NoGradContext:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return NoGradContext()

sys.modules['torch'] = DummyTorch()
sys.modules['torchvision'] = type('Mock', (object,), {})()
sys.modules['psutil'] = type('Mock', (object,), {'Process': lambda: type('P', (object,), {'cpu_percent': lambda self, *a, **k: 0, 'memory_percent': lambda self: 0})()})()
sys.modules['cv2'] = type('Mock', (object,), {})()

@pytest.fixture(autouse=True)
def setup_test_env():
    """
    Fixture global que executa antes de cada teste.
    Garante que as variaveis de ambiente criticas estejam configuradas para
    modo de teste (evitando abrir UI real ou conectar em DB de producao).
    """
    os.environ['CARINA_TEST_MODE'] = '1'
    # Evita que interfaces PyQt/PySide tentem usar X11 se estiver rodando em CI headless
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    # Evita que o OpenCV tente abrir janelas ou conectar ao GTK/Wayland
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'dummy'
    # O Torch JIT costuma travar na inicializacao em ambientes headless
    os.environ['PYTORCH_JIT'] = '0'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    yield
    
    # Cleanup apos o teste
    for key in ['CARINA_TEST_MODE', 'QT_QPA_PLATFORM', 'QT_MAC_WANTS_LAYER', 
                'OPENCV_VIDEOIO_PRIORITY_MSMF', 'OPENCV_FFMPEG_CAPTURE_OPTIONS',
                'PYTORCH_JIT', 'TF_ENABLE_ONEDNN_OPTS']:
        os.environ.pop(key, None)

from typing import Any

@pytest.fixture
def mock_snmp_hardware(monkeypatch):
    """
    Simula perfeitamente um Hardware SNMP sem gerar trafego de rede.
    Injeta interceptacoes de snmp_get e snmp_set diretamente na classe base.
    """
    # Importacao preguicosa para evitar ciclos de dependencia e hangs
    from src.drivers.base_driver import BaseTrafficDriver
    
    # Memoria RAM que atua como os registradores OID do Semaforo Virtual
    hardware_memory = {}
    
    def fake_snmp_get(self, oid: str):
        if oid in hardware_memory:
            return True, hardware_memory[oid] # Sucesso, Valor
        return False, "TIMEOUT (Simulated Timeout)" # Falha
        
    def fake_snmp_set(self, oid: str, value: Any, value_type: Any):
        hardware_memory[oid] = value
        return True, "Success"
        
    monkeypatch.setattr(BaseTrafficDriver, 'snmp_get', fake_snmp_get)
    monkeypatch.setattr(BaseTrafficDriver, 'snmp_set', fake_snmp_set)
    
    return hardware_memory

@pytest.fixture
def mock_logger(mocker):
    """
    Simula uma funcao de log generica para funcoes que esperam 
    um 'log_callback' (como o SignalRouter ou AppState).
    """
    return mocker.MagicMock()
