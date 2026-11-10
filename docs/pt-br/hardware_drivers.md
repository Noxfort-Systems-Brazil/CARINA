---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers, evp, tailscale]
aliases: [Hardware Drivers, Controladores Físicos, NTCIP 1202, Integração UTMC, Despachante EVP]
---

# 🚦 Drivers de Hardware, Controladores Semafóricos & Gateway de Borda

Este documento especifica a camada de integração física com controladores de tráfego do CARINA localizada em [`src/drivers/`](../../src/drivers), [`src/controller/`](../../src/controller) e no gateway de alta performance em [`src_go/`](../../src_go). Ele detalha os protocolos **NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**, o despachante de preempção de emergência (EVP), o servidor Web Gateway com túnel **Tailscale** e o fail-safe determinístico.

⬅️ Voltar ao [Portal Central MOC](carina_moc.md) | 🏛️ Ver [Arquitetura do Sistema](architecture.md) | 🛡️ Ver [Segurança e Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempção EVP](evp_and_preemption.md)

---

## 1. Visão Geral da Arquitetura de Hardware

O CARINA interage com controladores semafóricos reais de diversos fabricantes (Econolite, Siemens, Peek, SWARCO, Yunex) utilizando o **Gateway de Hardware em Go** (`bin/carina-go` compilado a partir de [`src_go/`](../../src_go)). A comunicação entre o núcleo Python do CARINA e o Gateway Go ocorre estritamente via **pipes padrão do sistema operacional (`stdin`/`stdout`)** com mensagens JSON delimitadas por quebra de linha (NDJSON). Isso garante **zero portas de rede abertas na máquina host** para comunicação IPC local, execução sub-milissegundo e imunidade total ao GIL do Python.

Além do controle semafórico NTCIP/UTMC padrão, o gateway em Go inclui o **Despachante de Preempção EVP** (`src_go/evp_go/dispatcher.go`) para retenção de fase em microssegundos e o **Web Gateway Remoto** (`src_go/web_gateway/server.go`), que provê conectividade segura via malha Tailscale, ingestão HTTP 204 na porta 2201 e transmissão Server-Sent Events (SSE) para videowalls CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │  (Estado & Pooling)  │   │   │ (Watchdog Heartbeat) │
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
                                  │ stdin / stdout (NDJSON IPC - Zero Portas Host)
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
      │  │  EVP Dispatcher  │ │  GoSNMP  │ │ TrapListener UDP │   │
      │  │ (Retenção OID)   │ │UDP Pt 161│ │    (Porta 162)   │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestão Web Remota & Malha
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │          Web Gateway & Malha Tailscale (Porta 2201)       │
      │  - POST /api/v1/evp/telemetry (Ingestão GPS HTTP 204)     │
      │  - GET /cco/stream (Hub SSE em Tempo Real para Videowall) │
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

### 2.2 Tabela de Mapeamento Padronizado de OIDs NTCIP

| Nome do Objeto | ASN.1 OID | Tipo | Descrição |
| :--- | :--- | :---: | :--- |
| `ascPhaseStatusGroupReds` | `1.3.6.1.4.1.1206.4.2.1.1.1` | `OCTET STRING` | Máscara de bits de fases atualmente em Vermelho. |
| `ascPhaseStatusGroupYellows` | `1.3.6.1.4.1.1206.4.2.1.1.2` | `OCTET STRING` | Máscara de bits de fases atualmente em Amarelo. |
| `ascPhaseStatusGroupGreens` | `1.3.6.1.4.1.1206.4.2.1.1.3` | `OCTET STRING` | Máscara de bits de fases atualmente em Verde. |
| `ascPhaseHold` | `1.3.6.1.4.1.1206.4.2.1.1.5` | `OCTET STRING` | Retém a fase verde ativa (impede encerramento do estágio). |
| `ascPhaseForceOff` | `1.3.6.1.4.1.1206.4.2.1.1.6` | `OCTET STRING` | Força o encerramento imediato do verde ativo. |
| `ascPhaseCall` | `1.3.6.1.4.1.1206.4.2.1.1.7` | `OCTET STRING` | Injeta chamada sintética de veículo para requisitar fase. |

---

## 3. Driver UTMC / UTMC2 (Padrão Britânico e Europeu)

Para interseções que operam sob a especificação do Reino Unido **Urban Traffic Management and Control (UTMC)**:
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Comunicação e gerenciamento de sessões UTMC em Go.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Decodificação de quadros e confirmações de estágio.
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Execução de demandas de estágio e movimentos de transição.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Mapeamento de estágios (Stage 1..8) para ações neurais do CARINA.
- [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Definições de OIDs UTMC2.

---

## 4. Despachante de Hardware de Preempção EVP (`src_go/evp_go/`)

O **Despachante de Preempção EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) trata requisições de corredores verdes de emergência em tempo real com atuação física em sub-milissegundos:

- **Bypass do Ciclo de Inferência:** As ordens de preempção ignoram o ciclo regular de decisão da rede neural e da coordenação semafórica, forçando a retenção do estágio semafórico de interesse da viatura.
- **Inserção de Retenção OID SNMP:** Converte o índice do estágio verde em máscara `ascPhaseHold` (`1.3.6.1.4.1.1206.4.2.1.1.5`), retendo os movimentos conflitantes em vermelho e assegurando passagem desimpedida.
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

### 6.1 Ciclo de Vida da Conexão (`src/controller/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py): Máquina de estados das conexões (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`).
- [`src/controller/connection_config_repo.py`](../../src/controller/connection_config_repo.py): Persistência de endereços IP, portas e credenciais na tabela `hardware_controller_connections`.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Execução do procedimento de reversão de emergência.

### 6.2 Fail-Safe Determinístico
1. **Perda de Heartbeat (< 500 ms):** Se a comunicação for interrompida por mais de 3 ciclos de polling, o CARINA libera imediatamente todos os comandos de `Hold` e `Force-Off`.
2. **Reversão Local:** O armário físico reverte imediatamente para seu plano coordenado fixo local (Time-of-Day) ou amarelo intermitente, garantindo segurança pública incondicional.
3. **Validação de Conflitos:** Toda atuação passa previamente pelo [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) antes do despacho, checando matrizes de conflito e tempos de entreverdes.

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
