---
tags: [api, grpc, hft, ipc, queues, telemetry, prometheus, evp, cco, ndjson]
aliases: [API Reference, Synapse HFT Protocol, IPC Channels, Telemetry Endpoints]
---

# ⚡ Referência de API, Protocolo Synapse HFT, Filas IPC & Endpoints CCO

Este documento serve como a especificação autoritativa das interfaces do ecossistema CARINA: o **Protocolo Synapse HFT via gRPC**, o catálogo de canais de **Comunicação Inter-Processos (IPC)**, o exportador Prometheus, a API de **Ingestão de Veículos de Emergência (EVP)**, os comandos NDJSON do **Go Gateway** e os endpoints REST/SSE da **Central de Controle Operacional (CCO)**.

⬅️ Voltar ao [Portal Central MOC](carina_moc.md) | 🏛️ Ver [Arquitetura do Sistema](architecture.md) | 🛡️ Ver [Segurança e Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempção EVP](evp_and_preemption.md)

---

## 1. Estruturas de Dados do Protocolo Synapse HFT (`proto/synapse_hft.proto`)

O CARINA se comunica com sensores de visão computacional, atuadores semafóricos e simuladores microscópicos (SUMO/CityFlow) via **gRPC** de sub-milissegundo:
- **Porta Padrão:** `50051` (configurável em `config/settings.ini` na seção `[SYNAPSE]`).
- **Transporte:** HTTP/2 sobre TCP com **TLS / mTLS** opcional (`grpc.ssl_server_credentials`) e **Autenticação por Token Bearer** (`BearerTokenServerInterceptor` em [`src/communication/grpc_security.py`](../../src/communication/grpc_security.py)) configurados via `CARINA_GRPC_AUTH_TOKEN`, `CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_TLS_CERT`, `CARINA_GRPC_TLS_KEY`, `CARINA_GRPC_TLS_CA` e `CARINA_GRPC_REQUIRE_CLIENT_CERT`. Aceita metadados `Authorization: Bearer <token>` ou `x-carina-token: <token>` verificados em tempo constante com `hmac.compare_digest`.
- **Pacote:** `synapse.hft`.

### 1.1 Definições Protobuf Principais

```protobuf
syntax = "proto3";
package synapse.hft;

// Mensagem de Telemetria de Tráfego de Alta Frequência
message TrafficFrame {
  int64 frame_id = 1;
  double timestamp = 2;
  string intersection_id = 3;
  repeated LaneMetric lane_metrics = 4;
}

message LaneMetric {
  string lane_id = 1;
  float occupancy = 2;            // 0.0 a 1.0
  float mean_speed_ms = 3;        // Velocidade média em metros por segundo
  int32 queue_length_vehicles = 4;// Contagem de veículos parados em fila
  float waiting_time_seconds = 5; // Tempo de espera acumulado
}

// Ação de Atuação Semafórica Despachada pelo Agente
message SignalGroupAction {
  string intersection_id = 1;
  int32 target_stage_index = 2;
  int32 duration_seconds = 3;
  bool is_force_off = 4;
}

// Estado de Retorno do Sistema e Liveness
message SystemState {
  string status = 1;              // "HEALTHY", "DEGRADED", "FAILSAFE"
  double current_sim_time = 2;
  int32 active_intersections = 3;
}
```

---

## 2. Métodos do Serviço Synapse HFT

```protobuf
service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

| Método RPC | Tipo | Latência Típica | Finalidade |
| :--- | :--- | :---: | :--- |
| **`Ping`** | Unário | $< 0,5\text{ ms}$ | Verificação ultra-rápida de liveness do barramento RPC. |
| **`LoadScenario`** | Unário | Varia | Inicializa grafos viários, nós e limites geodésicos. |
| **`SystemControl`** | Unário | $< 1\text{ ms}$ | Emite comandos globais do operador (`START`, `PAUSE`, `STOP`, `RESET`). |
| **`StreamTraffic`** | Client Streaming | $< 1\text{ ms}$ | Canal contínuo de fluxo de telemetria por via a $1\text{ Hz}$ ou $10\text{ Hz}$. |

---

## 3. Catálogo de Canais de Comunicação Inter-Processos (IPC)

O CARINA coordena **12 filas IPC delimitadas** e **1 conexão de pipe duplex thread-safe** (`ThreadSafePipeConnection` em [`src/communication/pipe_utils.py`](../../src/communication/pipe_utils.py)) gerenciadas por [`ProcessManager`](../../src/launcher/process_manager.py):

| Canal IPC | Tipo / Limite | Produtor | Consumidor | Formato / Esquema de Dados |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn` / `ai_conn`** | Pipe | `CentralController` ↔ `AI_Process` | Bidirecional | `("custom", "hft_step", ...)`, `("hft_telemetry_push", ...)`, `("ai_hardware_cmd", ...)`, `("ai_evp_preempt", ...)`, `("fenix_handover_complete", ...)` |
| **`wd`** | Fila (500) | `CentralController` / Microsserviços | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`fenix`** | Fila (50) | `Watchdog` / `CentralController` | `FenixSupervisionController` | `("TRIGGER_RESURRECTION", reason)` / `("HANDOVER_COMPLETE", payload)` |
| **`sds`** | Fila (500) | `CentralController` | `DashboardService` | `("hft_rich_update", payload)` (telemetria rápida de 0,5s e lenta de heatmap + `hardware_status`) |
| **`sas`** | Fila (500) | `CentralController` | `AnalysisService` | Quadros agregados de tráfego para persistência e warrants |
| **`ui`** | Fila (500) | `UITrayManager` / `LiveDataProvider` | `CentralController` | Comandos de UI, `set_hardware_connection`, `tailscale_*`, `fenix_post_resurrection` |
| **`ui_telemetry`** | Fila (500) | `DashboardService` | `LiveDataProvider` | Pacotes em memória para renderização fluida a 60 FPS |
| **`db`** | Fila (500) | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state)` |
| **`g_state`** | Fila (500) | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | Fila (500) | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | Fila (10) | `AnalysisService` | `InfrastructureClient` | Relatórios de warrants e tempos sugeridos de engenharia |
| **`mfd_trigger`** | Fila (10) | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | Fila (10) | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

---

## 4. Exportador de Métricas Prometheus

O CARINA inclui um endpoint Prometheus nativo na porta `8000` para integração com Grafana corporativo:

| Métrica | Tipo | Rótulos | Descrição |
| :--- | :---: | :--- | :--- |
| `carina_inference_latency_seconds` | Histogram | `agent_type`, `model` | Latência da rede neural PPO-TCN e ST-GATv2. |
| `carina_queue_depth` | Gauge | `queue_name` | Profundidade e saturação das filas IPC em tempo real. |
| `carina_guardian_vetoes_total` | Counter | `intersection_id`, `reason` | Total de intervenções de segurança executadas. |
| `carina_evp_preemptions_total` | Counter | `intersection_id`, `corporation` | Contagem de corredores verdes de emergência abertos. |
| `carina_hardware_drops_total` | Counter | `intersection_id`, `protocol` | Quedas de conexão física com controladores NTCIP/UTMC. |

---

## 5. Protocolos de Telemetria e Monitoramento Externo (`src/transports/`)

O CARINA transmite estados vitais e alertas para plataformas externas de gestão de tráfego via `MonitorClient` e [`src/transports/`](../../src/transports):

### 5.1 Esquemas de Dados de Telemetria

#### Alerta de Incidente (`noxfort/incidents/` ou POST HTTP)
```json
{
  "intersection_id": "cruzamento_av_jk_01",
  "level": "CRITICAL",
  "category": "HARDWARE_DISCONNECT",
  "message": "[FailsafeManager] Controlador perdeu conexão física. Revertendo para plano fixo.",
  "occurred_at": "2026-09-15T01:30:00Z",
  "is_active": true
}
```

#### Heartbeat Periódico (`noxfort/telemetry/` ou POST HTTP)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

---

## 6. API HTTP de Ingestão de Veículos de Emergência (EVP)

O Go Web Gateway compilado expõe um endpoint unidirecional (*fire-and-forget*) de alta vazão para transponders GPS veiculares:

- **Endpoint:** `POST /api/v1/evp/telemetry` (alias: `POST /amb` ou `POST /amb/`)
- **Porta:** `2201` (`CARINA_GATEWAY_PORT`, Go Web Gateway / Tailscale Funnel) ou `8085` (servidor Go EVP dedicado [`src_go/evp_go/`](../../src_go/evp_go))
- **Segurança:** Fail-closed quando `CARINA_GATEWAY_ENABLED=False` (retorna `503 Service Unavailable`); valida `CARINA_EVP_AUTH_TOKEN` em tempo constante via `Authorization: Bearer <token>`, `X-EVP-Token` ou `X-Auth-Token` (retorna `401 Unauthorized` em caso de falha) e suporta HTTPS/TLS (`CARINA_GATEWAY_TLS_CERT` / `CARINA_GATEWAY_TLS_KEY`).
- **Resposta:** `204 No Content` (retorno imediato para latência $< 0,5\text{ ms}$)
- **Esquema JSON:**
  ```json
  {
    "vehicle_id": "SAMU-01",
    "corporation": "SAMU",
    "latitude": -23.31028,
    "longitude": -51.16278,
    "speed_kmh": 65.4,
    "heading_deg": 180.0,
    "siren_active": true,
    "timestamp": 1789458600.0
  }
  ```

---

## 7. Catálogo de Comandos NDJSON do Go Hardware & Web Gateway

Comandos despachados do processo proprietário do CARINA (`CentralController`) para o binário `bin/carina-go` via pipes padrão anônimos (`stdin`/`stdout`):

| Comando (`cmd`) | Argumentos / Carga | Retorno | Descrição |
| :--- | :--- | :--- | :--- |
| **`ping`** | Nenhum | `"pong"` | Valida liveness do gateway ($< 1\text{ ms}$). |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `snmp_config`, `config_path`, `protocol`, `green_stages` | Metadados | Estabelece sessão SNMPv2c/v3 UDP e perfil JSON de OIDs customizado opcional. |
| **`disconnect`** | `intersection_id` | `success: true` | Fecha a conexão e libera o socket. |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | Aplica ação neural ou de segurança aos grupos focais físicos. |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `stage_idx`, `stage_codes`, `vehicle_id` | String de ação executada | Despacha retenções de preempção de estágio em microssegundos aos controladores. |
| **`cco_broadcast`** | `data: dict` | `success: true` | Transmite quadros de telemetria fire-and-forget aos clientes SSE conectados do CCO. |
| **`gateway_set_enabled`** / **`gateway_get_status`** | `enabled: bool` | JSON de status | Alterna a guarda ativa do Web Gateway (`503` quando desativado) ou inspeciona estado. |
| **`gateway_set_auth_tokens`** | `evp_auth_token`, `cco_auth_token`, `allowed_origin` | Flags de config | Rotaciona dinamicamente tokens EVP/CCO e origem CORS no gateway Go em execução. |
| **`tailscale_status`** / **`tailscale_enable`** / **`tailscale_disable`** | `port`, `domain` | JSON `TailscaleStatus` | Gerencia domínio Tailscale Funnel, estado do nó e URLs públicas do CCO. |
| **`emergency_release`** | Nenhum | `success: true` | Pausa heartbeats e libera retenções de fase preservando drivers para recuperação. |
| **`resume_control`** | Nenhum | `resumed: int` | Reinicia heartbeats pausados de controladores após recuperação do failsafe do Watchdog. |

---

## 8. Endpoints REST e SSE do Central Control Operator (CCO)

Disponíveis no Go Web Gateway na porta `2201` (`CARINA_GATEWAY_PORT`, HTTPS quando TLS estiver configurado, retornando `503 Service Unavailable` quando desabilitado):

- **`GET /` e `GET /health`**: Retorna o estado de integridade do sistema e a disponibilidade do gateway.
- **`GET /cco` e `GET /cco/`**: Serve a interface web compilada em React 18 do CCO.
- **`GET /cco/stream`**: Stream persistente Server-Sent Events (SSE) transmitindo estados dos semáforos, mapa de calor e posições de viaturas para videowalls (exige `CARINA_CCO_AUTH_TOKEN` via `Authorization: Bearer`, `X-CCO-Token` ou parâmetro de query `?token=`, além de CORS `CARINA_CCO_ALLOWED_ORIGIN`).
- **`GET /cco/topology`**: Serve geometrias viárias em GeoJSON/JSON, mapeamento de faixas e coordenadas de junções para renderização do mapa (protegido por token).
- **`POST /cco/broadcast`**: Endpoint de ingestão protegido chamado pelo [`CCOBroadcastClient`](../../src/sds/cco_broadcast_client.py) do SDS usando envio não-bloqueante *latest-wins*, autenticação `X-CCO-Token` e pinning de certificado SHA-256 opcional ([`PinnedHTTPSConnection`](../../src/sds/cco_tls_transport.py)).

---

## 9. Módulos Utilitários de Pacing, Maturação e Cobertura Semanal

Interfaces em Python disponibilizadas no núcleo do CARINA para controle temporal e maturação:

### 9.1 `EpisodeStepCalculator` (`src.utils.episode_step_calculator`)
Dimensiona dinamicamente a contagem de passos de cada episódio a partir da topologia viária:
- **`calculate(net_or_path: Union[str, Any], telemetry_delta_ms: float = 250.0) -> EpisodePacingResult`**
  Processa a malha viária (caminho XML/GZ ou instância de rede), unifica conexões bidirecionais de mão dupla, calcula a complexidade topológica $C_{\text{topo}}$, o relaxamento sub-linear e devolve dataclass imutável contendo `episode_steps`, `duration_seconds`, `child_episodes_1_week` e `teen_episodes_1_week`.

### 9.2 `WeeklyCoverageTracker` (`src.core.weekly_coverage_tracker`)
Rastreia a cobertura das 168 faixas horárias reais ($7\text{ dias} \times 24\text{ horas}$) com persistência atômica:
- **`register_step(raw_timestamp: float) -> Tuple[int, int]`**: Registra a passagem temporal do timestamp UNIX na matriz `(weekday, hour)`.
- **`is_week_completed() -> bool`**: Retorna `True` se todos os 168 slots horários da semana forem observados.
- **`get_completion_ratio() -> float`**: Retorna razão entre $0.0$ e $1.0$ de cobertura semanal.
- **`save_state() / load_state()`**: Salva e restaura atomicamente o estado em JSON.

### 9.3 `ActionAuthorizer` (`src.core.action_authorizer`)
Autoriza atuação física em hardware com base no estágio e calendário real:
- **`is_action_authorized(agent_id: str, maturity: Maturity, sim_time: float, raw_timestamp: float = 0.0) -> Tuple[bool, str]`**: Verifica se a ação é autorizada; para estágio `TEEN`, bloqueia atuação durante picos urbanos clássicos (06:30-09:00 e 17:00-19:30) ou conforme grade do Synapse.
- **`load_peak_schedule_json(schedule_data: dict) -> None`**: Injeta grade horária dinâmica de picos viários enviada pelo Synapse.

### 9.4 `MaturityPacingCalculator` (`src.promotion.maturity_pacing_calculator`)
- **`calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]`**: Retorna `(child_episodes, teen_episodes, child_steps, teen_steps)` respeitando estritamente o piso inviolável de 1 semana.
- **`apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool`**: Calcula e injeta as durações calibradas diretamente no gerenciador de maturação.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
