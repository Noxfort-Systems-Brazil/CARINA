# 🧪 Diretrizes de Testes e Validação de Qualidade

O CARINA comanda infraestrutura viária e semafórica crítica para a segurança pública. Confiabilidade absoluta, testes unitários determinísticos, mocks de controladores e validação contínua dos vetos de segurança são obrigatórios antes de qualquer alteração entrar em produção.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](architecture.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Execução da Suíte de Testes

### 1.1 Executar Todos os Testes em Python (`pytest`)
Utilizando o ambiente virtual local:
```bash
./.venv/bin/pytest tests/ -v
```

### 1.2 Gerar Relatório de Cobertura de Código
Para medir a cobertura de linhas e ramificações nos módulos sob `src/`:
```bash
./.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
O relatório HTML interativo é gerado em `htmlcov/index.html`.

### 1.3 Executar Testes Unitários Nativos do Gateway Go (`go test`)
Para executar os testes em Go que cobrem NTCIP, UTMC, traps e autodescoberta:
```bash
cd src_go && go test -v ./...
```

---

## 2. Estrutura da Suíte de Testes (94 Módulos Unitários + 5 de Integração)

A suíte de testes em `tests/` totaliza **401 testes automatizados** e cobre exaustivamente:
- **Agentes e Decisão:** `test_local_agent.py`, `test_guardian_agent.py`, `test_strategist_agent.py`, `test_core_components.py`, `test_core_action_authorizer.py`.
- **Subsistema F.E.N.I.X.:** `test_fenix_supervisor.py`, `test_fenix_process_runner.py`, `test_fenix_recovery_policy.py`, `test_fenix_state_reconciler.py` e `test_watchdog_fenix_integration.py`.
- **Gateway e Drivers:** `test_go_gateway_bridge.py`, `test_traffic_light_driver.py`, `test_traffic_modular_components.py`, `test_driver_factory_brand_model.py`, `test_hardware_event_listener.py`.
- **Configurações e Telemetria:** `test_settings_modular.py`, `test_settings_view.py`, `test_monitor_client.py`, `test_monitor_disconnect.py`.
- **Segurança e Contas:** `test_security_modular.py`, `test_security_manager.py`.
- **Explicabilidade e Laudos:** `test_captum_analyzer.py`, `test_xai_report_builder.py`, `test_multi_agent_modular_builder.py`.
- **Física de Tráfego:** `test_mfd_processor.py`, `test_mfd_report_generator.py`, `test_sas_report_generator.py`.
- **Interface e Mapa:** `test_planning_view.py`, `test_planning_architecture.py`, `test_live_canvas_map_widget.py`, `test_map_click_precision.py`.
- **Testes de Integração (`tests/integration/`):**
  - `test_system_integration.py` (ciclo completo gRPC de telemetria até atuação).
  - `test_gateway_ipc_pipeline.py` (pipeline IPC anônimo via pipes NDJSON com o Gateway Go).
  - `test_hft_performance_sla.py` (validação de latência de sub-milissegundo no loop HFT).
  - `test_postgres_migrations.py` (migrações de esquema Alembic no PostgreSQL).
  - `test_watchdog_resilience.py` (tolerância a falhas e recuperação por timeout do Watchdog).
