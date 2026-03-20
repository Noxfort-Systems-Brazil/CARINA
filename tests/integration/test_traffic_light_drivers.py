import pytest
from src.drivers.ntcip_driver import NtcipDriver
from src.drivers.utmc_driver import UtmcDriver

@pytest.fixture
def ntcip_driver():
    """Inicializa um Driver NTCIP conectado num IP dummy para os testes."""
    return NtcipDriver(ip_address="192.168.1.100", port=161, community_string="public")

@pytest.mark.integration
def test_ntcip_send_action(ntcip_driver, mock_snmp_hardware):
    """
    Cenario 1: Envio de Comando Seguro (Action Translation).
    Garante que a acao logica do CARINA e codificada na base matematica certa do NTCIP.
    """
    # CARINA decide forcar verde na Fase 3
    carina_decision = {'action_type': 'hold', 'phase': 3}
    
    # A base base 2 deve bit-shiftar (1 << (phase - 1)) = (1 << 2) = 4
    expected_octet = 4 

    # Executa a tradução e envio
    success = ntcip_driver.send_action(carina_decision)
    
    # Validações
    assert success is True, "Driver deve informar sucesso para a AI"
    # Garantir que bateu exatamente no OID industrial exigido pelo NTCIP 1202
    assert ntcip_driver.OID_PHASE_HOLD in mock_snmp_hardware
    # Garantir que a matemática bate
    assert mock_snmp_hardware[ntcip_driver.OID_PHASE_HOLD] == expected_octet

@pytest.mark.integration
def test_ntcip_telemetry_fidelity(ntcip_driver, mock_snmp_hardware):
    """
    Cenario 2: Ingestao de Telemetria Fiel.
    A memória do cruzamento real envia para nós como está a rua.
    """
    # Simulamos que os detectores fisicos responderam que as Fases 1 e 5 estao Verdes
    # Fases 1 (bit 0 = 1) e Fase 5 (bit 4 = 16) = 1 + 16 = 17
    mock_snmp_hardware[ntcip_driver.OID_PHASE_STATUS_GREENS] = 17
    mock_snmp_hardware[ntcip_driver.OID_PHASE_STATUS_REDS] = 0
    
    # O Driver deve buscar os dados na nossa memoria (SNMP via mock)
    telemetry = ntcip_driver.get_telemetry()
    
    assert telemetry['protocol'] == "NTCIP 1202"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 17
    assert telemetry['active_reds'] == 0

@pytest.mark.integration
def test_ntcip_connection_loss_resilience(ntcip_driver, mock_snmp_hardware):
    """
    Cenario 3: Resiliencia a Queda de Conexao ("Cabo de rede cortado").
    Garante que a falha da requisicao SNMP devolve OFFLINE sem Exception grave que pare o CARINA.
    """
    # A memoria está VAZIA. Quando o driver tentar rodar `snmp_get`, a nossa 
    # Fixture devolverá 'False, TIMEOUT' como programado.
    
    telemetry = ntcip_driver.get_telemetry()
    
    # A inteligencia base do Driver deve absorver o choque e retornar OFFLINE.
    assert telemetry['status'] == "offline"
    # Nao pode travar a engine e ainda deve preencher os dados primarios com zero/padroes nulos
    assert telemetry['active_greens'] == 0

@pytest.fixture
def utmc_driver():
    """Inicializa um Driver UTMC2 conectado num IP dummy para os testes."""
    return UtmcDriver(ip_address="192.168.1.101", port=161, community_string="public")

@pytest.mark.integration
def test_utmc_send_action(utmc_driver, mock_snmp_hardware):
    """
    Cenario 1 (UTMC2): Envio de Comando Seguro (Action Translation).
    Garante que a acao logica do CARINA e codificada na base matematica certa do UTMC (onde phase = stage).
    """
    # CARINA decide forcar verde no Stage 2
    carina_decision = {'action_type': 'force_off', 'phase': 2}
    
    # A base base 2 deve bit-shiftar (1 << (stage - 1)) = (1 << 1) = 2
    expected_octet = 2

    # Executa a tradução e envio
    success = utmc_driver.send_action(carina_decision)
    
    # Validações
    assert success is True, "Driver deve informar sucesso para a AI"
    # Garantir que bateu exatamente no OID industrial exigido pelo UTMC
    assert utmc_driver.OID_STAGE_FORCE_OFF in mock_snmp_hardware
    # Garantir que a matemática bate
    assert mock_snmp_hardware[utmc_driver.OID_STAGE_FORCE_OFF] == expected_octet

@pytest.mark.integration
def test_utmc_telemetry_fidelity(utmc_driver, mock_snmp_hardware):
    """
    Cenario 2 (UTMC2): Ingestao de Telemetria Fiel.
    A memória do cruzamento real envia para nós como está a rua.
    """
    # Simulamos que os detectores fisicos responderam que o Stage 3 esta verde (bit 2 = 4)
    mock_snmp_hardware[utmc_driver.OID_STAGE_STATUS_ACTIVE] = 4
    
    # O Driver deve buscar os dados na nossa memoria (SNMP via mock)
    telemetry = utmc_driver.get_telemetry()
    
    assert telemetry['protocol'] == "UTMC2"
    assert telemetry['status'] == "online"
    assert telemetry['active_greens'] == 4

@pytest.mark.integration
def test_utmc_connection_loss_resilience(utmc_driver, mock_snmp_hardware):
    """
    Cenario 3 (UTMC2): Resiliencia a Queda de Conexao ("Cabo de rede cortado").
    Garante que a falha da requisicao SNMP devolve OFFLINE sem Exception grave que pare o CARINA.
    """
    # A memoria está VAZIA.
    telemetry = utmc_driver.get_telemetry()
    
    assert telemetry['status'] == "offline"
    assert telemetry['active_greens'] == 0
