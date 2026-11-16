---
tags: [api, grpc, ipc, referencia, protobuf]
aliases: [Referencia de API, Synapse HFT, Colas IPC, Interfaz gRPC]
---

# ⚡ Referencia de API y Especificaciones del Protocolo Synapse HFT

Este documento constituye la especificación autoritativa de interfaces para CARINA. Abarca el **Protocolo gRPC Synapse HFT**, las **Métricas del Exportador Prometheus** y los **Esquemas de Comunicación Inter-Procesos (IPC)**.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🚨 Ver [Preempción EVP](evp_and_preemption.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🗄️ Ver [Base de Datos y Esquemas](database_and_schemas.md)

---

## 1. Definición del Servicio gRPC Synapse HFT (`proto/synapse_hft.proto`)

CARINA se conecta con sensores externos, controladores de tráfico físicos y entornos de microsimulación (SUMO/CityFlow) mediante el **Protocolo Synapse HFT** sobre gRPC.

- **Puerto Predeterminado:** `50051` (Configurable en `config/settings.ini` bajo `[SYNAPSE]`)
- **Transporte:** HTTP/2 sobre TCP con **TLS / mTLS** opcional (`grpc.ssl_server_credentials`) y **Autenticación por Token Bearer** (`BearerTokenServerInterceptor` en [`src/communication/grpc_security.py`](../../src/communication/grpc_security.py)) configurado vía `CARINA_GRPC_AUTH_TOKEN`, `CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_TLS_CERT`, `CARINA_GRPC_TLS_KEY`, `CARINA_GRPC_TLS_CA` y `CARINA_GRPC_REQUIRE_CLIENT_CERT`. Acepta metadatos `Authorization: Bearer <token>` o `x-carina-token: <token>` verificados en tiempo constante mediante `hmac.compare_digest`.
- **Paquete del Protocolo:** `synapse.hft`

```protobuf
syntax = "proto3";
package synapse.hft;

service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

### 1.1 Desglose de Métodos RPC gRPC

#### `Ping`
- **Solicitud:** `Empty`
- **Respuesta:** `SystemState` (retorna el estado del servidor, bandera booleana de actividad y marca temporal UTC `server_time`).
- **Meta de Latencia:** $< 1\text{ ms}$

#### `LoadScenario`
- **Solicitud:** `ScenarioDefinition` (transfiere la geometría binaria del mapa `.net.xml.gz`, nodos/aristas topológicas y el JSON de programación de horas pico extraído por el clasificador ADAGIO).
- **Respuesta:** `ScenarioStatus` (booleano `accepted` y mensaje de estado).

#### `SystemControl`
- **Solicitud:** `ControlCommand` (Acción Enum: `START`, `PAUSE`, `STOP`, `RESET`).
- **Respuesta:** `CommandResponse` (booleano `success` y cadena `new_state`).

#### `StreamTraffic`
- **Solicitud:** `stream TrafficFrame` (Streaming de alta frecuencia de ocupación de vías, velocidades vehiculares, longitudes de cola y densidades).
- **Respuesta:** `SystemState`

---

## 2. Esquemas de Mensajes de Telemetría y Control

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // Ratio [0.0 - 1.0] of road occupancy
  float mean_speed = 2;     // Space-mean speed in m/s
  int32 queue_length = 3;   // Number of stopped vehicles in queue
  float density = 4;        // Vehicles per kilometer
}
```

### 2.2 `ScenarioDefinition`
```protobuf
message ScenarioDefinition {
  string map_hash = 1;
  TopologyGraph graph = 2;
  MapGeometry geometry = 3;
  bytes map_file_content = 4;
  string map_file_name = 5;
  string peak_schedule_json = 6;
}
```

---

## 3. Especificaciones de las Colas de Comunicación Inter-Procesos (IPC)

CARINA coordina **12 colas IPC acotadas** y **1 conexión por tubería dúplex segura para hilos** (`ThreadSafePipeConnection` en [`src/communication/pipe_utils.py`](../../src/communication/pipe_utils.py)) gestionadas por [`ProcessManager`](../../src/launcher/process_manager.py):

| Nombre de Cola | Tamaño Máx | Proceso Productor | Proceso Consumidor | Esquema de Carga / Tipo de Mensaje |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn` / `ai_conn`** | Pipe | `CentralController` ↔ `AI_Process` | Bidireccional | `("custom", "hft_step", ...)`, `("hft_telemetry_push", ...)`, `("ai_hardware_cmd", ...)`, `("ai_evp_preempt", ...)`, `("fenix_handover_complete", ...)` |
| **`wd`** | 500 | `CentralController` / Microservicios | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`fenix`** | 50 | `Watchdog` / `CentralController` | `FenixSupervisionController` | `("TRIGGER_RESURRECTION", reason)` / `("HANDOVER_COMPLETE", payload)` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `("hft_rich_update", payload)` (telemetría rápida 0.5s y lenta de mapas de calor + `hardware_status`) |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Métricas históricas de tráfico para agregación en PostgreSQL |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | Comandos de UI, `set_hardware_connection`, `tailscale_*`, `fenix_post_resurrection` |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | Paquetes de telemetría en tiempo real sin puertos en memoria, congestión y madurez |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `InfrastructureClient` | Informes de justificación de ingeniería y recomendaciones semafóricas |
| **`mfd_trigger`** | 10 | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

Para la actuación sobre controladores físicos vía NTCIP y UTMC, consulte [Controladores de Hardware](hardware_drivers.md).

---

## 4. Métricas del Exportador Prometheus

El `MetricsManager` expone telemetría operacional en tiempo real en el **puerto HTTP 8001** (ruta `/metrics`).

```text
# Prometheus Metric Summary:
carina_step_latency_seconds_bucket{le="0.005"}   # gRPC telemetry to actuation latency histogram
carina_ppo_reward_total                          # Cumulative reward for PPO Tactical Agent
carina_guardian_veto_total{type="symbolic"}      # Counter of symbolic safety vetoes
carina_guardian_veto_total{type="neural"}        # Counter of PAE neural spillback vetoes
carina_mfd_network_density_veh_km               # Macroscopic network density
carina_mfd_network_flow_veh_hr                   # Macroscopic network throughput
carina_active_processes_count                    # Count of alive backend microservices
```

---

## 5. Telemetría de Monitoreo Externo y Protocolos de Sondeo (`src/transports/`)

CARINA despacha latidos de estado en tiempo real y alertas de hardware hacia paneles operacionales externos y plataformas de telemetría en la nube mediante [`MonitorClient`](../../src/communication/monitor_client.py) y [`src/transports/`](../../src/transports).

### 5.1 Cargas Útiles de Telemetría

#### Carga Útil de Alerta de Incidentes (`noxfort/incidents/` o HTTP POST)
```json
{
  "intersection_id": "cruzamento_av_jk_01",
  "level": "CRITICAL",
  "category": "HARDWARE_DISCONNECT",
  "message": "[FailsafeManager] Controller dropped connection. Reverting to fixed-time.",
  "occurred_at": "2026-09-15T01:30:00Z",
  "is_active": true
}
```

#### Carga Útil de Telemetría de Latido (`noxfort/telemetry/` o HTTP POST)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

### 5.2 Protocolos de Transporte

| Protocolo | Ejemplo Config (`CARINA_MQTT_HOST`) | Implementación | Características |
| :--- | :--- | :--- | :--- |
| **Broker MQTT** | `127.0.0.1:1883` o `broker.emqx.io` | [`MonitorMqttTransport`](../../src/transports/mqtt_transport.py) | Paho MQTT v2, keepalive 60s, tópicos `noxfort/telemetry/` y `noxfort/incidents/`. |
| **HTTP / HTTPS REST** | `https://monitor.noxfort.com/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | JSON `POST`, `requests.Session` persistente, reintento exponencial, timeout 3.0s. |
| **Túneles Cloud (Ngrok)** | `https://xxxx.ngrok-free.dev/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | Detección automática vía `endpoint_resolver.py` enrutando mediante túnel HTTPS seguro. |

### 5.3 Reglas de Clasificación de Endpoints
La función de fábrica [`create_monitor_transport()`](../../src/transports/factory.py) resuelve automáticamente el transporte adecuado:
1. Si la cadena del host comienza con `http://` o `https://` $\implies$ **Transporte HTTP**.
2. Si la cadena del host contiene `.ngrok`, `.run.app` o una ruta `/api/` $\implies$ **Transporte HTTP** (antepone automáticamente `https://` si se omitió el esquema).
3. Si la cadena del host contiene una dirección IP o dominio con puerto opcional (ej. `10.0.0.1:1883`) $\implies$ **Transporte MQTT**.

---

## 6. API HTTP de Ingestión de Telemetría de Vehículos de Emergencia

El Gateway Web compilado en Go expone ingestión unidireccional de alto rendimiento (fire-and-forget) para transpondedores GPS de vehículos de emergencia:

- **Endpoint:** `POST /api/v1/evp/telemetry` (alias: `POST /amb` o `POST /amb/`)
- **Puerto:** `2201` (`CARINA_GATEWAY_PORT`, Gateway Web en Go / Tailscale Funnel) o `8085` (servidor Go EVP dedicado [`src_go/evp_go/`](../../src_go/evp_go))
- **Seguridad:** Opera en modo *fail-closed* cuando `CARINA_GATEWAY_ENABLED=False` (responde `503 Service Unavailable`); valida `CARINA_EVP_AUTH_TOKEN` en tiempo constante mediante `Authorization: Bearer <token>`, `X-EVP-Token` o `X-Auth-Token` (responde `401 Unauthorized` si no coincide) y soporta HTTPS/TLS (`CARINA_GATEWAY_TLS_CERT` / `CARINA_GATEWAY_TLS_KEY`).
- **Respuesta:** `204 No Content` (Retorno inmediato para ejecución en sub-milisegundos)
- **Esquema del Payload:**
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

## 7. Conjunto de Comandos NDJSON IPC del Gateway de Hardware y Web en Go

Comandos despachados desde el proceso propietario de CARINA (`CentralController`) hacia `bin/carina-go` mediante tuberías anónimas estándar (`stdin`/`stdout`):

| Comando (`cmd`) | Argumentos / Carga Útil | Datos de Respuesta | Descripción |
| :--- | :--- | :--- | :--- |
| **`ping`** | Ninguno | `"pong"` | Verifica la vitalidad del gateway ($< 1\text{ ms}$). |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `snmp_config`, `config_path`, `protocol`, `green_stages` | Metadatos de conexión | Establece sesión SNMPv2c/v3 UDP y perfil opcional JSON de OIDs personalizados. |
| **`disconnect`** | `intersection_id` | `success: true` | Cierra la conexión y libera el socket. |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | Aplica la acción neuronal o de seguridad a los grupos semafóricos físicos. |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `stage_idx`, `stage_codes`, `vehicle_id` | Cadena de acción ejecutada | Despacha retenciones de fase de preempción en microsegundos a controladores de campo. |
| **`cco_broadcast`** | `data: dict` | `success: true` | Transmite tramas de telemetría fire-and-forget a clientes SSE de CCO conectados. |
| **`gateway_set_enabled`** / **`gateway_get_status`** | `enabled: bool` | JSON de estado | Alterna la guarda activa del Web Gateway (`503` al estar deshabilitado) o inspecciona su estado. |
| **`gateway_set_auth_tokens`** | `evp_auth_token`, `cco_auth_token`, `allowed_origin` | Banderas de configuración | Rota dinámicamente los tokens EVP/CCO y el origen CORS en el gateway Go en ejecución. |
| **`tailscale_status`** / **`tailscale_enable`** / **`tailscale_disable`** | `port`, `domain` | JSON `TailscaleStatus` | Gestiona el dominio Tailscale Funnel, estado del nodo y URLs públicas del CCO. |
| **`emergency_release`** | Ninguno | `success: true` | Pausa los latidos y libera las retenciones de fase preservando los drivers para recuperación. |
| **`resume_control`** | Ninguno | `resumed: int` | Reinicia los latidos pausados de los controladores tras la recuperación de failsafe del Watchdog. |

---

## 8. Endpoints REST y SSE del Operador del Centro de Control (CCO)

Disponibles en el puerto `2201` del Gateway Web en Go (`CARINA_GATEWAY_PORT`, HTTPS cuando TLS está configurado, respondiendo `503 Service Unavailable` cuando está deshabilitado):

- **`GET /` y `GET /health`**: Retorna el estado de salud del sistema y la disponibilidad del gateway.
- **`GET /cco` y `GET /cco/`**: Sirve la interfaz web compilada en React 18 del CCO.
- **`GET /cco/stream`**: Stream persistente de Server-Sent Events (SSE) que transmite estados de señales en tiempo real, mapas de calor de congestión y ubicaciones de vehículos de emergencia hacia los videowalls (exige `CARINA_CCO_AUTH_TOKEN` vía `Authorization: Bearer`, `X-CCO-Token` o parámetro `?token=`, además de CORS `CARINA_CCO_ALLOWED_ORIGIN`).
- **`GET /cco/topology`**: Sirve geometrías de tramos viales en GeoJSON/JSON, mapeos de carriles y coordenadas de intersecciones para el renderizado del mapa (protegido por token).
- **`POST /cco/broadcast`**: Endpoint protegido de ingestión invocado por [`CCOBroadcastClient`](../../src/sds/cco_broadcast_client.py) de SDS utilizando agrupación no bloqueante *latest-wins*, autenticación `X-CCO-Token` y fijación opcional de certificados SHA-256 ([`PinnedHTTPSConnection`](../../src/sds/cco_tls_transport.py)).

---

## 9. Módulos Utilitarios de Pacing, Maduración y Cobertura Semanal

Interfaces en Python del núcleo de CARINA para el control temporal y de maduración:

### 9.1 `EpisodeStepCalculator` (`src.utils.episode_step_calculator`)
Calcula dinámicamente los pasos por episodio a partir de la topología de la red vial:
- **`calculate(net_or_path: Union[str, Any], telemetry_delta_ms: float = 250.0) -> EpisodePacingResult`**
  Procesa la red SUMO, unifica sentidos bidireccionales, descarta conectores internos (`:`), calcula la complejidad topológica $C_{\text{topo}}$, el tiempo de relajación sub-lineal $T_{\text{físico}}$ y devuelve un `EpisodePacingResult` con `episode_steps`, `duration_seconds` y los pisos semanales de episodios (`child_episodes_1_week`, `teen_episodes_1_week`).

### 9.2 `WeeklyCoverageTracker` (`src.core.weekly_coverage_tracker`)
Rastrea la observación a lo largo de las 168 horas del calendario real ($7\text{ días} \times 24\text{ horas}$) con persistencia atómica:
- **`register_step(raw_timestamp: float) -> Tuple[int, int]`**: Registra tramas de telemetría en la matriz `(dia_semana, hora)` según timestamps UNIX reales.
- **`is_week_completed() -> bool`**: Retorna `True` si se han cubierto las 168 ranuras horarias de la semana.
- **`get_completion_ratio() -> float`**: Retorna la proporción actual de cobertura semanal en $[0.0, 1.0]$.
- **`save_state() / load_state()`**: Guarda y restaura atómicamente el progreso en disco (`weekly_coverage_{phase}.json`), tolerando pausas y reinicios del proceso.

### 9.3 `ActionAuthorizer` (`src.core.action_authorizer`)
Autoriza la actuación física en hardware según la fase de madurez y el calendario real:
- **`is_action_authorized(agent_id: str, maturity: Maturity, sim_time: float, raw_timestamp: float = 0.0) -> Tuple[bool, str]`**: Evalúa si el agente puede actuar sobre controladores físicos. Restringe a los agentes `TEEN` a periodos fuera de hora punta, forzando modo sombra durante las horas punta clásicas (06:30-09:00 y 17:00-19:30 de lunes a viernes) o según la programación de Synapse.
- **`load_peak_schedule_json(schedule_data: dict) -> None`**: Carga programaciones dinámicas de periodos punta enviadas por Synapse.

### 9.4 `MaturityPacingCalculator` (`src.promotion.maturity_pacing_calculator`)
- **`calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]`**: Retorna `(child_episodes, teen_episodes, child_steps, teen_steps)` acotado al piso inviolable de 1 semana ($E_{\text{semana}} \times S \times \Delta t \ge 604.800\text{ s}$).
- **`apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool`**: Inyecta automáticamente las duraciones dinámicas calculadas en el `MaturityManager`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
