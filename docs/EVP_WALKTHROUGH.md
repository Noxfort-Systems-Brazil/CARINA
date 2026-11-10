# Walkthrough: Módulo de Preempção de Veículos de Emergência (EVP)

Implementação completa do módulo **Emergency Vehicle Preemption (EVP)** na arquitetura da **CARINA_CORE** e **src_go**, em estrita conformidade com **SOLID + DDD + Flat Architecture**, respeito às normas de segurança do **CONTRAN** e comunicação **100% unidirecional (Fire-and-Forget)** para antenas GPS veiculares.

---

## 1. O Que Foi Desenvolvido

### Camada de Domínio & Serviço (`src/evp/` - Flat Architecture)
- [`evp_models.py`](../src/evp/evp_models.py): Entidades de domínio com tipagem estrita (`CorporationType`, `TelemetryData`, `EmergencyVehicle`).
- [`evp_kinematics.py`](../src/evp/evp_kinematics.py): Motor cinemático geodésico (Haversine WGS84). Identifica o gatilho espacial de **Início da Quadra** ($60\text{ m} \le \text{dist} \le 160\text{ m}$) e detecção de **Checkout** pós-cruzamento.
- [`evp_service.py`](../src/evp/evp_service.py): Singleton central de ciclo de vida e orquestração de preempção. Reaproveita integralmente as regras físicas e transições regulamentares (amarelo e all-red) da CARINA ([`SafetyRules`](../src/utils/safety_rules.py) e [`StageTransitionManager`](../src/manager/stage_transition_manager.py)), emitindo `ACTION_HOLD` (1) no estágio alvo e `ACTION_ADVANCE` (0) nos divergentes, com watchdog de segurança em $45\text{ s}$.
- [`evp_bridge.py`](../src/evp/evp_bridge.py): Interceptador de segurança que liga o `EVPService` ao [`SafetyAuditor`](../src/core/safety_auditor.py) e despacha via IPC de ultra-baixa latência para o `GoGatewayClient`.
- [`evp_http_server.go`](../src_go/evp_go/evp_http_server.go): Servidor HTTP nativo em Go (porta `8085` ou `2201` via Web Gateway) para ingestão das antenas GPS veiculares (`POST /api/v1/evp/telemetry` retornando `204 No Content` unidirecional).
- [`evp_repository.py`](../src/evp/evp_repository.py): Persistência assíncrona na tabela `evp_telemetry_records`.
- [`evp_notifier.py`](../src/evp/evp_notifier.py): Notificador thread-safe (Observer) para a Flet UI.

### Camada de Hardware de Alta Velocidade (`src_go/evp_go/`)
- [`types.go`](../src_go/evp_go/types.go) e [`dispatcher.go`](../src_go/evp_go/dispatcher.go): Dispatcher em Go compilado para comandos rápidos de preempção semafórica.
- Integrado no roteador [`router.go`](../src_go/cmd/gateway/router.go) sob o comando `"evp_preempt"`.

### Banco de Dados & Schemas
- Expandido o delta de decisão de 0-5 para **0-6 (`6: EVP_PREEMPTION`)** em [`step_decision_repo.py`](../src/repositories/step_decision_repo.py), [`step_decision_worker.py`](../src/database/step_decision_worker.py), [`schema_queries.json`](../config/database/schema_queries.json) e [`docs/DATABASE_AND_SCHEMAS.md`](DATABASE_AND_SCHEMAS.md).
- Tabela criada: `evp_telemetry_records` com índice `idx_evp_veh_time`.

### Camada Visual & Flet UI
- [`evp_vehicle_marker.py`](../ui/widgets/evp_vehicle_marker.py): Marcadores visuais desenhados com geometrias CONTRAN:
  - **SAMU**: $\Delta$ Triângulo (Branco / Vermelho Vivo)
  - **Bombeiros**: $\square$ Quadrado (Laranja / Vermelho Fogo)
  - **Polícia**: $\bigcirc$ Círculo (Azul Escuro / Azul Royal)
  - **Sirene Ativa**: Efeito de piscar síncrono com o `blink_toggle` do [`MapAnimator`](../ui/animators/map_animator.py).
- [`evp_vehicle_card.py`](../ui/widgets/evp_vehicle_card.py): Card modal flutuante com telemetria ao clicar na viatura.
- [`evp_fleet_connection_card.py`](../ui/cards/evp_fleet_connection_card.py) e [`evp_safety_parameters_card.py`](../ui/cards/evp_safety_parameters_card.py): Aba dedicada "Preempção (EVP)" no modal Configurações do Sistema com importação/exportação de CSV de conexão da frota, status em tempo real e ajustes CONTRAN.
- Integrado na navegação em [`ui/main_ui.py`](../ui/main_ui.py), [`navigation_manager.py`](../ui/managers/navigation_manager.py), [`dashboard_view.py`](../ui/views/dashboard_view.py) e [`live_canvas_map_widget.py`](../ui/widgets/live_canvas_map_widget.py).

### Ferramenta de Testes e Simulação
- [`demo/evp_vehicle_simulator.py`](../demo/evp_vehicle_simulator.py): Simulador CLI standalone para teste de corridas de emergência e patrulha contínua.

---

## 2. Resultados de Verificação

### Testes Unitários Automatizados (`pytest`)
Executados via `.venv/bin/pytest tests/unit/test_evp_service.py -v`:
```
tests/unit/test_evp_service.py::test_corporation_type_and_models PASSED  [ 16%]
tests/unit/test_evp_service.py::test_evp_kinematics_engine PASSED        [ 33%]
tests/unit/test_evp_service.py::test_contran_rules_action_evaluation PASSED [ 50%]
tests/unit/test_evp_service.py::test_evp_service_two_factor_trigger PASSED [ 66%]
tests/unit/test_evp_service.py::test_evp_bridge_safety_auditor_interception PASSED [ 83%]
tests/unit/test_evp_service.py::test_evp_http_receiver_unidirectional PASSED [100%]

============================== 6 passed in 0.79s ===============================
```

### Compilação do Gateway Go
Executado em `src_go/`:
```bash
go build -v ./...
# Exit Code: 0 (Sucesso sem erros)
```

### Teste de Ingestão HTTP Unidirecional Ponta a Ponta
Disparo simulado da antena GPS:
```
=======================================================
🚨 INICIANDO SIMULAÇÃO DE CORRIDA DE EMERGÊNCIA
Viatura: SAMU-01 (SAMU) 🔺 (Triângulo)
Sirene: LIGADA | Destino: http://localhost:18086/api/v1/evp/telemetry
=======================================================

[18:31:15] SAMU-01 | Dist:  220.0m | DISTANTE (>160m) | HTTP 204 [OK]
[18:31:16] SAMU-01 | Dist:  211.0m | DISTANTE (>160m) | HTTP 204 [OK]
[18:31:16] SAMU-01 | Dist:  201.9m | DISTANTE (>160m) | HTTP 204 [OK]
[18:31:17] SAMU-01 | Dist:  192.9m | DISTANTE (>160m) | HTTP 204 [OK]
```

---

## 3. Como Executar e Testar

1. **Executar a CARINA com interface gráfica:**
   ```bash
   python carina.py
   ```
   - O receptor HTTP subirá automaticamente na porta `8085`.
   - A nova aba **"Preempção EVP"** estará disponível na barra superior.

2. **Simular uma corrida de emergência (SAMU com sirene ligada):**
   ```bash
   .venv/bin/python demo/evp_vehicle_simulator.py --vehicle SAMU-01 --mode emergency
   ```
   - No mapa ao vivo, o triângulo do SAMU piscará e avançará em direção ao cruzamento.
   - Ao atingir entre 60m e 160m, o semáforo abrirá corredor verde (`HOLD`).
   - Ao transpor o cruzamento (checkout), o semáforo é liberado imediatamente.

3. **Simular frota completa em patrulha (SAMU, Bombeiros e PM):**
   ```bash
   .venv/bin/python demo/evp_vehicle_simulator.py --mode patrol --duration 30
   ```
