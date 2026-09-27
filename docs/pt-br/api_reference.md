# ⚡ Referência de API, Protocolo Synapse HFT e Filas IPC

Este documento serve como a especificação autoritativa das interfaces do CARINA, abrangendo o **Protocolo Synapse HFT via gRPC**, os canais de **Comunicação Inter-Processos (IPC)** e as métricas do exportador Prometheus.

⬅️ [Central de Documentação](../README.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Definição do Serviço Synapse HFT (`proto/synapse_hft.proto`)

O CARINA se comunica com sensores de visão computacional, atuadores semafóricos e simuladores microscópicos (SUMO/CityFlow) via **gRPC**:
- **Porta Padrão:** `50051` (configurável em `config/settings.ini`).
- **Transporte:** HTTP/2 sobre TCP com TLS opcional.
- **Pacote:** `synapse.hft`.

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

### 1.1 Métodos RPC Principais
- **`Ping`:** Checagem de liveness com latência de resposta $< 1\text{ ms}$.
- **`LoadScenario`:** Carrega geometria viária (`.net.xml.gz`), nós topológicos e agendamentos.
- **`SystemControl`:** Comandos operacionais (`START`, `PAUSE`, `STOP`, `RESET`).
- **`StreamTraffic`:** Streaming contínuo de alta frequência com ocupação, velocidades médias e filas por via.

---

## 2. Especificação das Filas IPC (`multiprocessing`)

O CARINA gerencia 10 canais IPC delimitados criados por `ProcessManager`:

| Fila | Limite | Produtor | Consumidor | Formato / Esquema de Mensagem |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Pipe | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Pipe | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | Todos os Microsserviços | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Métricas agregadas de tráfego para PostgreSQL |
| **`ui`** | 500 | `UITrayManager` / UI | `CentralController` | Comandos de UI, overrides e parâmetros de temporização |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | Pacotes em memória de telemetria em tempo real para o Flet |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |

---

## 3. Protocolos de Telemetria e Monitoramento Externo (`src/transports/`)

O CARINA transmite estados vitais e alertas para plataformas externas de gestão de tráfego via `MonitorClient`:
- **Corretor MQTT:** Tópicos `noxfort/telemetry/` e `noxfort/incidents/` (QoS 0/1).
- **HTTP / HTTPS REST:** Envio automático via requisições `POST` JSON com sessões persistentes e backoff exponencial (suporte nativo a URLs de túneis Cloud e Ngrok).
