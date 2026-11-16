---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers, evp, tailscale]
aliases: [Hardware Drivers, Controladores Físicos, NTCIP 1202, Integração UTMC, Despachante EVP]
---

# 🚦 Drivers de Hardware, Controladores Semafóricos & Gateway de Borda

Este documento especifica a camada de integração física com controladores de tráfego do CARINA localizada em [`src/drivers/`](../../src/drivers), [`src/controller/`](../../src/controller) e no gateway de alta performance em [`src_go/`](../../src_go). Ele detalha os protocolos **NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**, o despachante de preempção de emergência (EVP), o servidor Web Gateway com túnel **Tailscale** e o fail-safe determinístico.

⬅️ Voltar ao [Portal Central MOC](carina_moc.md) | 🏛️ Ver [Arquitetura do Sistema](architecture.md) | 🛡️ Ver [Segurança e Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempção EVP](evp_and_preemption.md)

---

## 1. Visão Geral da Arquitetura de Hardware

O CARINA interage com controladores semafóricos reais de diversos fabricantes (Econolite, Siemens, Peek, SWARCO, Yunex) utilizando o **Gateway de Hardware em Go** (`bin/carina-go` compilado a partir de [`src_go/`](../../src_go)). A comunicação entre o núcleo Python do CARINA e o Gateway Go ocorre estritamente via **pipes padrão do sistema operacional (`stdin`/`stdout`)** com mensagens JSON delimitadas por quebra de linha (NDJSON). Isso garante **zero portas IPC locais abertas na máquina host**, execução sub-milissegundo e imunidade total ao GIL do Python.

### 1.1 Propriedade Única do Gateway (`CARINA_GATEWAY_ROLE`) & Arquitetura em Malha Fechada
Para evitar processos `bin/carina-go` duplicados, colisões na porta UDP `162` do listener de traps e estado SNMP em *split-brain*:
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`):** Inicializa exclusivamente `bin/carina-go`, hospeda [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (composto por `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` e `TailscaleGatewayAdapter`), gerencia as conexões SNMP locais do `HardwareConnectionManager` e transmite snapshots aos workers a jusante.
- **`AI_Process`, `SDS` e `UI` (`CARINA_GATEWAY_ROLE=remote`):** Operam como espelhos remotos sem lançar binários Go locais nem vincular UDP `162`. [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py) (materializado por [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py)) encaminha ações (`ai_hardware_cmd`) e preempções EVP (`ai_evp_preempt`) de volta ao `CentralController` por meio de [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Decodificação de Telemetria em Malha Fechada:** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) e [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) traduzem máscaras de bits reais dos controladores (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) em índices de estágio 0-based do SUMO para extração de estado da IA e reconciliação de handover do F.E.N.I.X.

Além do controle semafórico NTCIP/UTMC padrão, o gateway em Go inclui o **Despachante de Preempção EVP** (`src_go/evp_go/dispatcher.go`) para retenção de fase em microssegundos e o **Web Gateway Remoto** (`src_go/web_gateway/server.go`), que provê conectividade segura autenticada por token via malha Tailscale, terminação TLS, ingestão HTTP na porta 2201 e transmissão Server-Sent Events (SSE) para videowalls CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │      CentralController (CARINA_GATEWAY_ROLE=owner)     │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │  (Estado & SNMPv2/v3)│   │   │ (Watchdog Heartbeat) │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │(Despacho Preempção)  │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Subprocesso Pipe Py)   │
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - Zero Portas Controle Locais)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │          GATEWAY DE HARDWARE CARINA (Binário Go)          │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │    Driver NTCIP    │         │    Driver UTMC     │   │
      │   │ (NTCIP 1202 v02)   │         │ (UTMC2 Padrão UK)  │   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │  EVP Dispatcher  │ │GoSNMPv2/3│ │ Decod. Trap Bin. │   │
      │  │ (Retenção OID)   │ │UDP Pt 161│ │ (SNMPv1/v2c/v3)  │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestão Web Remota & Malha
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │        Web Gateway & Malha Tailscale (Porta 2201 / TLS)   │
      │  - Fail-closed por padrão (HTTP 503 quando desativado)    │
      │  - POST /api/v1/evp/telemetry (Auth Token, HTTP 204)      │
      │  - GET /cco/stream (Auth Token, CORS, SSE Videowall)      │
      │  - Tailscale Funnel / Rede de Borda Criptografada P2P     │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. Driver NTCIP 1202 Actuated Signal Controller (ASC)

O padrão **NTCIP 1202** (National Transportation Communications for ITS Protocol) é a norma predominante na América do Norte e no Brasil em controladores semafóricos modernos.

### 2.1 Arquitetura de Módulos
**Implementação no Gateway Go (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go): Orquestrador nativo do driver NTCIP em Go.
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go): Poller de telemetria para fases ativas, anéis e detectores.
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go): Injetor de retenção de fase (`hold`), force-off e chamadas.
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go): Traduz ações discretas do CARINA em máscaras de bits NTCIP.
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) e [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json): Perfis de OID embutidos no binário.

**Camada de Proxy e Adaptação em Python (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py): Cliente IPC gerenciando o subprocesso `bin/carina-go`.
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py): Proxy Liskov (`BaseTrafficDriver`) transparente para o motor de IA.
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py): Instanciação automática com autodetecção de fabricante.

### 2.2 Tabela de Mapeamento Padronizado de OIDs NTCIP (`src_go/configs/ntcip_oids.json`)

Todos os OIDs de status (`phaseStatusGroup`) e controle (`phaseControlGroup`) do NTCIP 1202 suportam PDUs inteiros e `OCTET STRING`/`BitString` via [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go), podendo ser sobrescritos por interseção via `config_path`:

| Chave do Objeto | ASN.1 OID | Grupo / Tipo | Descrição |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | Status / Bitmask | Máscara de bits de fases atualmente em Vermelho. |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | Status / Bitmask | Máscara de bits de fases atualmente em Amarelo. |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | Status / Bitmask | Máscara de bits de fases atualmente em Verde. |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | Status / Bitmask | Chamadas ativas de detecção veicular reportadas pelo controlador. |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | Status / Bitmask | Chamadas ativas de botoeira de pedestres reportadas pelo controlador. |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | Controle / Bitmask | Omite fases específicas do serviço. |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | Controle / Bitmask | Retém a fase verde ativa (`ascPhaseControlHold`). |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | Controle / Bitmask | Força o encerramento do verde ativo (`ascPhaseControlForceOff`). |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | Controle / Bitmask | Injeta chamada sintética de veículo (`ascPhaseControlVehCall`). |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | Controle / Bitmask | Injeta chamada sintética de pedestre (`ascPhaseControlPedCall`). |

---

## 3. Driver UTMC / UTMC2 & Suporte SNMPv3 USM

Para interseções que operam sob a especificação do Reino Unido **Urban Traffic Management and Control (UTMC)** ou armários de campo com autenticação **SNMPv3**:
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Comunicação e gerenciamento de sessões UTMC em Go com `Probe()` e `CloseTransport()` thread-safe.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Confirmação de estágios (`status_active`, `status_leaving`, `status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`, `status_ped_demand`).
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Execução de demandas de estágio, hold, force-off e ações lógicas seguras quanto a entreverdes.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Mapeamento de estágios (Stage 1..8) para ações neurais do CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) e [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Definições embutidas de OIDs UTMC2.
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go): **Motor SNMPv3 USM** suportando `NoAuthNoPriv`, `AuthNoPriv` e `AuthPriv` com protocolos de autenticação (`MD5`, `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512`) e criptografia de privacidade (`DES`, `AES`, `AES192`, `AES256`, `AES192C`, `AES256C`). Metadados JSON `snmp_config` e sobrescritas de OIDs via `config_path` por interseção propagam de [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) e [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) através da [`DriverFactory`](../../src/drivers/driver_factory.py) até o `GoGatewayClient`.

---

## 4. Despachante de Hardware de Preempção EVP (`src_go/evp_go/`)

O **Despachante de Preempção EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) trata requisições de corredores verdes de emergência em tempo real com atuação física em sub-milissegundos:

- **Bypass do Ciclo de Inferência:** As ordens de preempção ignoram o ciclo regular de decisão da rede neural e da coordenação semafórica, forçando a retenção do estágio semafórico de interesse da viatura.
- **Inserção de Retenção OID SNMP:** Converte os índices dos estágios verdes (`stage_idx` e `stage_codes`) em máscaras de bits `phase_control.hold` NTCIP (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) ou retenção de estágio UTMC, retendo os movimentos conflitantes em vermelho e assegurando passagem desimpedida.
- **Protocolo IPC em Microssegundos:** Acionado via comando NDJSON `evp_preempt`:
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **Watchdog e Liberação Failsafe:** As retenções são liberadas assim que a viatura cruza a linha de retenção ($\le 15\text{ m}$) ou na expiração do tempo limite do watchdog ($45\text{ s}$). Se o processo de controle cair, o hardware em campo reverte automaticamente após 3 heartbeats perdidos.

---

## 5. Gateway Web Remoto & Rede em Malha (`src_go/web_gateway/`)

Para redes metropolitanas inteligentes onde viaturas de socorro ou operadores centrais necessitam de acesso remoto sem exposição de IP público:

- **Malha Criptografada Tailscale:** Integrada através de [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go), permitindo aos controladores de borda do CARINA formar uma rede privada de confiança zero (*zero-trust*).
- **Tailscale Funnel (Porta 2201):** Expõe publicamente os endpoints de telemetria sob TLS seguro sem requerer abertura manual de portas em roteadores de rua.
- **Receptor de Telemetria de Alta Vazão:** Expõe `POST /api/v1/evp/telemetry` (HTTP 204) para recepção de sinais GPS veiculares com resposta imediata.
- **Hub de Transmissão Server-Sent Events (SSE):** [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) transmite estados dos semáforos, alertas e posições das viaturas para videowalls CCO via `GET /cco/stream`.

---

## 6. Gestão de Conexões e Fail-Safe Determinístico

### 6.1 Ciclo de Vida da Conexão & Pooling (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) e [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py): Gerenciam máquinas de estado de conexão (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`), visões passivas espelhadas no modo `remote` (`update_remote_hardware_status`), autodetecção de portas de simuladores ([`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)) e restauração em lote via CSV ([`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)).
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) e [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py): Persistem endpoints IP e JSON `snmp_config` opcional (SNMPv3 USM / `config_path` de OIDs customizados) em `hardware_controller_connections` e templates CSV, preservando [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) como fachada retrocompatível.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Executa a reversão de emergência via `HardwareGatewayCoordinator.on_failsafe_triggered()` e recuperação via `on_failsafe_recovered()`.

### 6.2 Determinismo de Fail-Safe, Recuperação & Traps SNMP Binárias
1. **Perda de Heartbeat & Fail-Safe Reversível:** Se a comunicação com um controlador ativo cair ou o failsafe do Watchdog disparar, `EmergencyReleaseControlAll()` pausa os heartbeats e libera retenções de fase mantendo drivers SNMP e o listener de traps vivos para que `resume_control` (`ResumeControlAll()`) retome suavemente na recuperação. No encerramento do processo ou `EOF`/`SIGPIPE`, `ShutdownAll()` libera retenções permanentemente e fecha os sockets.
2. **Proteção de Entreverdes (`HardwareStageActuator`):** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) ignora chamadas conflitantes de `send_stage_hold` durante intervalos de entreverde amarelo/vermelho total (`_is_intergreen_stage`) e resolve IDs prefixados com `tl_` uniformemente.
3. **Decodificador Binário de Traps SNMPv1/v2c/v3 (`src_go/pkg/traplistener/snmp_decoder.go`):** Decodifica pacotes binários ASN.1 BER Trap/Inform na porta UDP `162` (`CARINA_TRAP_PORT`), classificando alarmes `coldStart`, `warmStart`, `linkDown`, `linkUp`, `authenticationFailure`, NTCIP (`.1206.*`) e UTMC (`.13267.*`, `.2825.*`) por severidade (`CRITICAL`, `WARNING`, `INFO`).
4. **Validação de Conflitos:** Toda atuação passa previamente pelo [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) antes do despacho, checando matrizes de conflito e tempos de entreverdes.

### 6.3 Reporte e Filtro de Incidentes (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py): Intercepta mudanças de estado do hardware e monta mensagens de alerta padronizadas.
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py): Evita tempestades de notificações através de cache com timestamp em `.carina_incident_filter_cache.json`.
- Despacha alertas dinamicamente via `MonitorClient` para corretores MQTT ou endpoints HTTP/Webhook.

---

## 7. Segurança & Credenciais de Rede

As credenciais de hardware nunca devem ser gravadas diretamente no código. O CARINA resolve credenciais e senhas SNMP através de variáveis de ambiente no [`.env`](../../.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

Para detalhes de segurança, consulte [Segurança & Autenticação](security_and_auth.md).
Para esquemas de serialização de telemetria, veja a [Referência de API](api_reference.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
