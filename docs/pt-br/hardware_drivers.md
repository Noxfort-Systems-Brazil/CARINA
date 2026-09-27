# 🚦 Drivers de Hardware e Integração com Controladores Semafóricos

Este documento especifica a camada de integração física com controladores de tráfego do CARINA localizada em `src/drivers/`, `src/controller/` e no gateway compilado em `src_go/`. Ele detalha os protocolos **NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**, o gerenciamento de conexões, a aquisição de telemetria e o fail-safe determinístico.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](../pt-br/architecture.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Visão Geral da Arquitetura de Hardware

O CARINA interage com controladores semafóricos reais de diversos fabricantes (Econolite, Siemens, Peek, SWARCO, Yunex) utilizando o **Gateway de Hardware em Go** (`bin/carina-go` compilado a partir de `src_go/`). A comunicação entre o núcleo Python do CARINA e o Gateway Go ocorre estritamente via **pipes padrão do sistema operacional (`stdin`/`stdout`)** com mensagens JSON delimitadas por quebra de linha (NDJSON). Isso garante **zero portas de rede abertas na máquina host**, latência sub-milissegundo e imunidade total ao GIL do Python.

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       ┌──────────────────────┐        ┌──────────────────────┐
       │  ConnectionManager   │        │ FailsafeManager      │
       │  (Estado & Pooling)  │        │ (Watchdog Heartbeat) │
       └──────────┬───────────┘        └──────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Subprocesso Pipe Py)   │
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - Zero Portas Host)
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │          GATEWAY DE HARDWARE CARINA (Binário Go)      │
      │                    (bin/carina-go)                    │
      │                                                       │
      │   ┌────────────────────┐     ┌────────────────────┐   │
      │   │    Driver NTCIP    │     │    Driver UTMC     │   │
      │   │ (NTCIP 1202 v02)   │     │ (UTMC2 Padrão UK)  │   │
      │   └─────────┬──────────┘     └─────────┬──────────┘   │
      │             │                          │              │
      │             └─────────────┬────────────┘              │
      │                           │                           │
      │             ┌─────────────┴─────────────┐             │
      │             ▼                           ▼             │
      │  ┌──────────────────────┐    ┌─────────────────────┐  │
      │  │    Cliente GoSNMP    │    │  TrapListener UDP   │  │
      │  │    (Porta UDP 161)   │    │     (Porta 162)     │  │
      │  └──────────────────────┘    └─────────────────────┘  │
      └───────────────────────────────────────────────────────┘
```

---

## 2. Driver NTCIP 1202 Actuated Signal Controller (ASC)

O padrão **NTCIP 1202** é amplamente utilizado na América do Norte e em sistemas inteligentes de transporte (ITS) modernos.

### 2.1 Arquitetura de Módulos
**Implementação no Gateway Go (`src_go/`):**
- `src_go/pkg/ntcip/driver.go`: Orquestrador nativo do driver NTCIP em Go.
- `src_go/pkg/ntcip/telemetry.go`: Poller de telemetria para fases ativas, anéis e detectores.
- `src_go/pkg/ntcip/action_executor.go`: Injetor de retenção de fase (`hold`), force-off e chamadas.
- `src_go/pkg/ntcip/stage_mapper.go`: Traduz ações discretas do CARINA em máscaras de bits NTCIP.
- `src_go/pkg/ntcip/config.go` e `src_go/configs/ntcip_oids.json`: Perfis dinâmicos de OID embutidos no binário.

**Camada de Proxy e Adaptação em Python (`src/drivers/`):**
- `src/drivers/go_gateway_client.py`: Cliente IPC gerenciando o subprocesso `bin/carina-go`.
- `src/drivers/go_driver_proxy.py`: Proxy Liskov (`BaseTrafficDriver`) transparente para o motor de IA.
- `src/drivers/driver_factory.py`: Instanciação automática baseada em autodetecção de fabricante.

---

## 3. Driver UTMC / UTMC2 (Padrão Britânico e Europeu)

Para interseções que operam sob a especificação do Reino Unido **Urban Traffic Management and Control (UTMC)**:
- `src_go/pkg/utmc/driver.go`: Comunicação e gerenciamento de sessões UTMC em Go.
- `src_go/pkg/utmc/telemetry.go`: Decodificação de quadros e confirmações de estágio.
- `src_go/pkg/utmc/action_executor.go`: Execução de demandas de estágio e movimentos de transição.
- `src_go/pkg/utmc/stage_mapper.go`: Mapeamento de estágios (Stage 1..8) para ações neurais do CARINA.
- `src_go/configs/utmc_oids.json`: Mapeamento de OIDs UTMC2.

---

## 4. Gestão de Conexões e Fail-Safe Determinístico

### 4.1 Ciclo de Vida da Conexão (`src/controller/connection_manager.py`)
Controla a máquina de estados semafórica: `DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`.

### 4.2 Fail-Safe Determinístico
1. **Perda de Heartbeat (< 500 ms):** Se a comunicação for interrompida por mais de 3 ciclos de polling, o CARINA libera imediatamente todos os comandos de `Hold` e `Force-Off`.
2. **Reversão Local:** O armário físico reverte imediatamente para seu plano coordenado fixo local (Time-of-Day) ou amarelo intermitente, garantindo segurança pública incondicional.
3. **Validação de Conflitos:** Toda atuação passa previamente pelo `StageValidator` antes do despacho, checando matrizes de conflito e tempos de entreverdes.

### 4.3 Reporte e Filtro de Incidentes (`src/drivers/`)
- `IncidentReporter`: Dispara alertas padronizados para o painel de operações e transporte polimórfico (`MonitorClient`).
- `IncidentFilter`: Cache com timestamp em `.carina_incident_filter_cache.json` para evitar tempestades de alarmes repetidos.
