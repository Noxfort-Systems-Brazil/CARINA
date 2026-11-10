---
tags: [testes, pytest, cobertura, mocks, seguranca, validacao]
aliases: [Diretrizes de Teste, Testes Unitários, Mocks de Segurança, Garantia da Qualidade]
---

# 🧪 Diretrizes de Teste & Validação

O CARINA governa infraestruturas críticas de trânsito urbano. Confiabilidade absoluta, testes unitários determinísticos, mocks de drivers de campo e validação contínua de vetos de segurança são mandatórios antes de qualquer liberação de código em produção.

⬅️ [Central de Documentação](carina_moc.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🛠️ [Guias do Desenvolvedor](developer_guides.md) | 🚑 [Preempção de Emergência (EVP)](evp_and_preemption.md)

---

## 1. Executando a Suíte de Testes (`pytest`)

O CARINA dispõe de uma suíte exaustiva contendo **861 testes automatizados** (verificados via `pytest --collect-only`), garantindo zero regressões, segurança rigorosa e comutação fail-safe em microssegundos em todos os subsistemas. Todos os testes residem no diretório [`tests/`](../../tests).

### 1.1 Executar Todos os Testes
```bash
pytest tests/ -v
```

### 1.2 Gerar Relatórios de Cobertura
Para mensurar a cobertura de linhas e ramificações em `src/`:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
O relatório HTML detalhado é gerado em `htmlcov/index.html`.

### 1.3 Executar Testes Unitários do Gateway Go (`go test`)
Para executar os testes unitários nativos em Go cobrindo NTCIP, UTMC, traps e descoberta de rede:
```bash
cd src_go && go test -v ./...
```

---

## 2. Estrutura Real de Diretórios de Testes

```text
tests/
├── conftest.py                     # Fixtures compartilhadas do pytest, bancos temporários & mocks de ambiente
├── mock_junctions.py               # Grafo sintético de topologia & nós de teste
├── benchmark.py                    # Benchmarks de desempenho (taxa de transferência & latência)
│
├── unit/                           # Testes Unitários Isolados (Total de 861 Testes Coletados)
│   ├── test_evp_service.py         # Ciclo de vida do EVPService, pipeline de ingestão & gatilhos de preempção
│   ├── test_evp_kinematics.py      # Distância geodésica Haversine, velocidade, azimute & portais de aproximação
│   ├── test_evp_preemption_engine.py # Arbitragem de retenção verde, watchdog de dwell de 45s & entreverdes
│   ├── test_evp_map_topology.py    # Casamento de topologia viária, aproximações de entrada & fases alvo
│   ├── test_evp_fleet_persistence.py # Operações de CRUD de viaturas autorizadas & cache de placas
│   ├── test_evp_config_repo.py     # Repositório de configurações de EVP & persistência de limiares
│   ├── test_evp_fleet_controller.py # Lógica de negócios de frotas de emergência & validação
│   ├── test_evp_fleet_csv.py       # Exportação e importação em lote de frotas via CSV
│   ├── test_evp_fleet_save_flow.py # Fluxo de ponta a ponta do formulário UI de viaturas até o banco
│   ├── test_evp_hardware_parity_persistence.py # Paridade de estado de hardware entre motores de banco
│   ├── test_evp_settings_handler.py # Persistência de parâmetros EVP em settings.ini & .env
│   ├── test_evp_vehicle_marker.py  # Glifos de viaturas na tela Flet & animações de estroboscópio
│   ├── test_local_agent.py         # Seleção de ações do PPO Tactical Agent & loop de atualização
│   ├── test_guardian_agent.py      # Sentinela de segurança D3QN & validação de limiares de risco
│   ├── test_strategist_agent.py    # Coordenador arterial ST-GATv2 Lite com atenção em grafo
│   ├── test_settings_modular.py    # SettingsService modular, Schemas, Provedores & arquivo INI
│   ├── test_settings_view.py       # Tela Flet de configurações & persistência via UI
│   ├── test_monitor_client.py      # MonitorClient polimórfico, transportes HTTP & MQTT
│   ├── test_monitor_disconnect.py  # Tentativas de reconexão, esvaziamento de buffers & desconexão
│   ├── test_core_components.py     # Testes do DecisionCoordinator & ActionAuthorizer
│   ├── test_go_gateway_bridge.py   # Subprocesso do Gateway Go & ponte IPC por pipes anônimos
│   ├── test_traffic_light_driver.py # Abstração de alto nível do driver de sinal semafórico
│   ├── test_traffic_modular_components.py # Componentes modulares de controladores semafóricos
│   ├── test_driver_factory_brand_model.py # Fábrica de instanciação de drivers (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # Escutas de traps SNMP & decodificação de falhas
│   ├── test_connection_db_persistence.py  # Persistência de endpoints de controladores
│   ├── test_connection_manager_orchestrator.py # Máquina de estados de conexão de controladores
│   ├── test_fenix_supervisor.py    # Ciclo de vida do FENIX supervisor, recuperação & ressurreição
│   ├── test_fenix_process_runner.py # Controle de processos do runner (SIGTERM/SIGKILL)
│   ├── test_fenix_recovery_policy.py # Política de recuperação com janela temporal & backoff exponencial
│   ├── test_fenix_state_reconciler.py # Transição segura de controle & sincronização FROZEN_SYNC
│   ├── test_watchdog_fenix_integration.py # Disparo por timeout do Watchdog para ressurreição no FENIX
│   ├── test_security_modular.py    # AuthService, UserService, PBKDF2 & Bloqueio por tentativas
│   ├── test_security_manager.py    # Validação da fachada legada SecurityManager
│   ├── test_captum_analyzer.py     # Atribuição de importância neural via Integrated Gradients
│   ├── test_xai_report_builder.py  # Geração de laudos ABNT em Word com equações em OMML
│   ├── test_multi_agent_modular_builder.py # Montagem modular de blocos do laudo pericial
│   ├── test_mfd_processor.py       # Processador central do Diagrama Fundamental Macroscópico
│   ├── test_mfd_report_generator.py # Geração de relatórios MFD & ajuste de curvas
│   ├── test_mfd_db_reconstruction.py # Reconstrução de dados MFD a partir de tabelas PostgreSQL
│   ├── test_mfd_new_report.py      # Pipeline de novo relatório do MFD
│   ├── test_sas_report_generator.py # Testes de justificativas de engenharia no Smart Analysis System
│   ├── test_sas_data_transducer.py # Transdutor de telemetria do SAS
│   ├── test_sas_helpers.py         # Auxiliares de cálculo matemático do SAS
│   ├── test_sas_mfd_db_cache.py    # Cache de banco de dados do SAS MFD
│   ├── test_semantic_transducer_device.py # Transdutor de SLM offline & alocação em VRAM
│   ├── test_planning_view.py       # Testes da tela Flet de planejamento topológico
│   ├── test_planning_architecture.py # Apresentador da tela de planejamento & exportadores
│   ├── test_planning_export_handler.py # Exportadores de planos semafóricos em CSV
│   ├── test_planning_panel_presenter.py # Apresentador do painel lateral de planejamento
│   ├── test_live_canvas_map_widget.py # Desenho customizado da tela Flet renderizando vias e semáforos
│   ├── test_map_interaction_precision.py # Matemática de zoom, deriva de coordenadas & hit-testing
│   ├── test_map_event_router_precision.py # Desambiguação de cliques entre semáforos e faixas
│   ├── test_interactive_map_precision.py # Precisão de toques e seleção de camadas no mapa
│   ├── test_planning_map_sync.py   # Raio de tolerância do PlanningMapRenderer & sincronismo de tela
│   ├── test_live_data_provider_ipc.py # Transmissão de filas IPC em memória no LiveDataProvider
│   ├── test_watchdog.py            # Lógica de batimento cardíaco (heartbeat) & cronômetros de processos
│   ├── test_consolidation_purge.py # Consolidação e expurgo de dados delta na fluidodinâmica
│   ├── test_csv_template_export_import.py # Importação e exportação de templates de controladores em CSV
│   ├── test_db_schema_isolation.py # Isolamento de esquemas de banco para execução de testes
│   ├── test_infrastructure_client.py # Cliente para justificativas de infraestrutura
│   ├── test_intersection_state_manager.py # Rastreamento de estágios multi-interseções
│   ├── test_main_components.py     # Componentes principais do CentralController
│   ├── test_manual_override_hft.py # Intervenções manuais de fase em alta frequência
│   ├── test_pushdown_query.py      # Avaliação de consultas SQL pushdown
│   ├── test_tls_state_provider.py  # Provedor de estados de semáforos
│   ├── test_ui_main_orchestrator.py # Orquestração principal da interface de usuário
│   ├── test_window_manager.py      # Gerenciamento de ciclo de vida da janela desktop
│   ├── test_population_manager_pbt.py # Isolamento de coortes PBT & proteção contra divergência de tensores
│   ├── test_performance_margin_calculator.py # Margem de graduação fluida & telemetria de infância
│   ├── test_reward_weights_calculator.py # Balanceamento físico de recompensas (tempo de travessia HCM)
│   ├── test_maturity_pacing_calculator.py # Ritmo automático de duração de fases por topologia viária
│   ├── test_yellow_schedule_manager.py # Avaliador de agendamento de amarelo intermitente noturno
│   └── test_yellow_schedule_card.py # Cartão Flet de agendamento de amarelo & controles de horário
│
└── integration/                    # Testes de Integração de Sistema Ponta a Ponta (5 Módulos)
    ├── test_system_integration.py    # Ciclo completo de telemetria gRPC até a atuação semafórica
    ├── test_gateway_ipc_pipeline.py  # Pipeline IPC por pipes anônimos NDJSON com o Gateway Go
    ├── test_hft_performance_sla.py   # Latência do loop HFT em sub-milissegundos & validação de SLA
    ├── test_postgres_migrations.py   # Migrações e reversões de esquemas PostgreSQL via Alembic
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
