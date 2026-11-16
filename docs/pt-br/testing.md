---
tags: [testes, pytest, cobertura, mocks, seguranca, validacao]
aliases: [Diretrizes de Teste, Testes Unitários, Mocks de Segurança, Garantia da Qualidade]
---

# 🧪 Diretrizes de Teste & Validação

O CARINA governa infraestruturas críticas de trânsito urbano. Confiabilidade absoluta, testes unitários determinísticos, mocks de drivers de campo e validação contínua de vetos de segurança são mandatórios antes de qualquer liberação de código em produção.

⬅️ [Central de Documentação](carina_moc.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🛠️ [Guias do Desenvolvedor](developer_guides.md) | 🚑 [Preempção de Emergência (EVP)](evp_and_preemption.md)

---

## 1. Executando a Suíte de Testes (`pytest`)

O CARINA dispõe de uma suíte exaustiva contendo **967 testes Python automatizados** (verificados via `pytest --collect-only`: **935 testes unitários** em 192 arquivos, **18 testes de integração** em 8 arquivos e **14 testes** em 4 arquivos de teste raiz) além de **46 testes unitários em Go** em 15 arquivos `*_test.go`, garantindo zero regressões, segurança rigorosa e comutação fail-safe em microssegundos em todos os subsistemas. Todos os testes residem em [`tests/`](../../tests) e [`src_go/`](../../src_go).

### 1.1 Executar Testes com Guarda de Memória (`scripts/pytest_limited.sh`)
Para impedir que fixtures multiprocesso de PyTorch/SLM esgotem a RAM do host durante execuções completas, prefira o executor limitado no kernel [`scripts/pytest_limited.sh`](../../scripts/pytest_limited.sh) em conjunto com [`tests/memory_guard.py`](../../tests/memory_guard.py):
```bash
# Impõe limites cgroup v2 do systemd (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# ou recorre a ulimit -d + guarda de RSS da árvore de processos via CARINA_PYTEST_MAX_RAM_MB:
./scripts/pytest_limited.sh tests/ -v
```
- **Recuperação Determinística de Recursos:** `tests/memory_guard.py` amostra o RSS da árvore de processos, executa `gc.collect()` / `malloc_trim()` suaves e limpa singletons (`GoGatewayClient`, `HardwareConnectionManager`, `DatabaseManager`, figuras do Matplotlib) via `reclaim_test_resources()`.
- **Guarda de SLM Offline em Testes:** O carregamento real de GGUF de LLM fica desabilitado durante o `pytest` por padrão, a menos que `CARINA_ALLOW_REAL_SLM=1` seja explicitamente exportada.

### 1.2 Executar Todos os Testes Diretamente & Relatórios de Cobertura
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
O relatório HTML detalhado é gerado em `htmlcov/index.html`.

### 1.3 Executar Testes Unitários do Gateway Go (`go test`)
Para executar os testes unitários nativos em Go (46 funções de teste cobrindo NTCIP, UTMC, SNMPv3/codec, traps binárias, descoberta de rede, failsafe, EVP e auth/TLS do Web Gateway):
```bash
cd src_go && go test -v -race ./...
```

---

## 2. Estrutura Real de Diretórios de Testes

```text
tests/
├── conftest.py                     # Fixtures compartilhadas do pytest, bancos temporários & mocks de ambiente
├── memory_guard.py                 # Monitor RSS da árvore de processos, trims suaves de GC & recuperação de singletons
├── mock_junctions.py               # Grafo sintético de topologia & nós de teste
├── benchmark.py                    # Benchmarks de desempenho (taxa de transferência & latência)
├── test_*.py                       # 4 suítes raiz (14 testes: sanidade, invariantes, pacing, cobertura semanal)
│
├── unit/                           # Testes Unitários Isolados (192 arquivos / 935 testes coletados)
│   ├── test_closed_loop_hardware_control.py # Decodificação de máscaras NTCIP/UTMC & sincronia de estágio em malha fechada
│   ├── test_field_readiness_configs.py # config_path por interseção, repasse de tokens & temporização de fases
│   ├── test_grpc_security.py       # Testes de TLS/mTLS do Synapse gRPC & BearerTokenServerInterceptor
│   ├── test_sds_cco_broadcast_security.py # TLS do CCOBroadcastClient + pinning de certificado folha SHA-256
│   ├── test_guardian_calibration_and_training.py # Treinamento QR-D3QN em CHILD, calibração F2, Noisy-OR & congelamento
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool, pragmas SQLite WAL & db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE, torch.vmap, GAE em NumPy, ReplayMemory no host
│   ├── test_phase2_db_ipc_optimizations.py # SQL make_interval, ThreadSafePipeConnection & retenção EVP
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock, VRAM pynvml, mpl_utils, cache XAI
│   ├── test_phase4_gateway_evp_ui_optimizations.py # Pausa de janela do MapAnimator, paginação do AuditLog, perf CCO
│   ├── test_pytest_memory_guard.py # Amostragem RSS da árvore de processos, trims suaves & recuperação de recursos
│   ├── test_solid_full_audit_refactoring.py # Interfaces segregadas & decomposições SOLID de coordenadores
│   ├── test_solid_gateway_and_step_refactoring.py # Testes DIP do coordenador de gateway & pipeline de passos
│   ├── test_evp_*.py               # 12 módulos de EVP (serviço, cinemática, preempção, frota, marcadores na UI)
│   ├── test_local_agent.py         # Seleção de ações do PPO Tactical Agent & loop de atualização
│   ├── test_guardian_agent.py      # Sentinela de segurança D3QN & validação de limiares de risco
│   ├── test_strategist_agent.py    # Coordenador arterial ST-GATv2 Lite com atenção em grafo
│   ├── test_pae_model.py           # Testes do iTransformer PAE condicionado à ação & incerteza
│   ├── test_remote_gateway_and_cco.py # Testes do Tailscale Web Gateway & stream CCO
│   ├── test_settings_modular.py    # SettingsService modular, Schemas, Provedores & arquivo INI
│   ├── test_monitor_client.py      # MonitorClient polimórfico, transportes HTTP & MQTT
│   ├── test_go_gateway_bridge.py   # Subprocesso do Gateway Go & ponte IPC por pipes anônimos
│   ├── test_fenix_*.py             # FENIX supervisor, runner, política de recuperação & reconciliador de estado
│   ├── security/                   # Suítes de criptografia, PBKDF2, política de senhas & segurança SOLID
│   └── ...                         # Cobertura completa em core, mfd, sas, xai, rendering & ui
│
└── integration/                    # Testes de Integração de Sistema Ponta a Ponta (8 Módulos / 18 Testes)
    ├── test_system_integration.py    # Ciclo completo de telemetria gRPC até a atuação semafórica
    ├── test_gateway_ipc_pipeline.py  # Pipeline IPC por pipes anônimos NDJSON com o Gateway Go
    ├── test_gateway_ownership_and_fenix_roundtrip.py # Propriedade CARINA_GATEWAY_ROLE owner/remote & roundtrip FENIX
    ├── test_go_gateway_snmp_hil_loopback.py # Loopback HIL entre binário Go real compilado <-> agente mock SNMP
    ├── test_hft_performance_sla.py   # Latência do loop HFT em sub-milissegundos & validação de SLA
    ├── test_postgres_migrations.py   # Migrações e reversões de esquemas PostgreSQL via Alembic
    ├── test_traffic_light_drivers.py # Verificações de integração de alto nível de drivers NTCIP/UTMC
    └── test_watchdog_resilience.py   # Failover por perda de heartbeat do Watchdog & ressurreição
```

---

## 3. Escrevendo Testes de Veto de Segurança (`SafetyAuditor`)

Qualquer nova ação ou proposta de transição de fase deve ser validada contra o [`src/core/safety_auditor.py`](../../src/core/safety_auditor.py):

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """Verifica que o auditor veta trocas prematuras de fase antes do verde mínimo expirar."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # Simula estado atual: Fase 1 ativa há apenas 3.0 segundos
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Tentativa de trocar para a Fase 2 prematuramente

    # Audita a ação
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forçado a manter a fase ativa
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """Verifica a Regra SR-00: preempção ativa força verde de emergência respeitando entreverdes."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # Agente neural propôs Fase 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forçado para o estágio alvo do EVP (Estágio 1)
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. Mocks de Drivers de Hardware

Ao testar controladores de tráfego sem equipamento físico conectado em bancada, utilize as fixtures de simulação fornecidas em [`tests/conftest.py`](../../tests/conftest.py) para emular respostas SNMP UDP:

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
