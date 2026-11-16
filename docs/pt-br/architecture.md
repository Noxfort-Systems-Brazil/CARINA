---
tags: [arquitetura, nucleo, sistema, gatv2, pae, pbt, amp, multiprocessamento]
aliases: [Arquitetura do Sistema, Blueprint Multiprocesso, Visão Geral do Sistema]
---

# 🏛️ CARINA: Blueprint do Sistema e Arquitetura de Multiprocessamento

Este documento especifica a arquitetura interna de engenharia do ecossistema CARINA. Ele detalha os 8 microsserviços concorrentes em processos do sistema operacional, a topologia canônica de redes neurais profundas (LocalAgent PPO-TCN, GuardianAgent D3QN e StrategistAgent ST-GATv2 Lite), o `TopologicalScaler`, os drivers de controladores físicos e o motor assíncrono de persistência com compressão delta no PostgreSQL.

⬅️ [Central Master de Documentação](carina_moc.md) | 🚨 [Preempção de Emergência (EVP)](evp_and_preemption.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🧠 [Notas de Pesquisa & Formulações](research_notes.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Modelo de Concorrência de Microsserviços Multiprocesso

O Global Interpreter Lock (GIL) do Python impede inferência de IA intensiva em CPU e operações pesadas de I/O em verdadeiro paralelismo multithread. Para garantir latência de atuação em sub-milissegundos, o CARINA implementa um **modelo de microsserviços multiprocesso** orquestrado por [`carina.py`](../../carina.py) e [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py) (modularizado com [`backend_service_registry.py`](../../src/launcher/backend_service_registry.py), [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py) e [`worker_entrypoints.py`](../../src/launcher/worker_entrypoints.py)), combinado com um **Gateway Industrial de Hardware & Web em Go** (`bin/carina-go`) de propriedade exclusiva do `CentralController` (`CARINA_GATEWAY_ROLE=owner`):

```mermaid
graph TD
    Launcher[carina.py / Bandeja de Sistema - remote] -->|Inicializa e Monitora| PM[ProcessManager]

    PM --> CC[1. Processo CentralController - owner]
    PM --> AI[2. Motor AI_Process - remote]
    PM --> WD[3. Processo Watchdog]
    PM --> SDS[4. DashboardService SDS - remote]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Motor MFD_Worker]

    CC <-->|ThreadSafePipeConnection| AI
    CC -->|Fila wd Heartbeats| WD
    WD -->|Fila fenix| PM
    AI -->|Fila db| DB
    CC -->|Fila sds| SDS
    CC -->|Fila sas| SAS
    CC -->|Fila mfd_trigger| MFD
    MFD -->|Fila mfd_results| CC
    SAS -->|Fila sas_results| CC
    XAI -->|Logs HFT em Disco| AI

    CC <-->|Tubo Anônimo Stdin/Stdout NDJSON| GW[Go Gateway carina-go]
    GW --> NTCIP[Controladores NTCIP 1202 / UTMC2 UDP 161]
    GW --> WebGW[Go Web Gateway Porta 2201 / TLS / Tailscale]
    WebGW --> CCO[Videowall CCO React/TSX src_tsx]
    WebGW <--|POST 204 Auth Token| EVP[Antenas GPS EVP Porta 8085 / 2201]
```

### 1.1 Propriedade Única do Gateway (`CARINA_GATEWAY_ROLE`) & Sincronia de Hardware em Malha Fechada
Para evitar sondagem SNMP dividida (*split-brain*), conflitos na porta `162` de traps e processos filhos `carina-go` duplicados entre workers multiprocesso:
- **Processo Proprietário (`CARINA_GATEWAY_ROLE=owner`):** Definido estritamente dentro de [`execute_controller_process`](../../src/launcher/worker_entrypoints.py) para o `CentralController`. Inicializa o [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (composto por `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` e `TailscaleGatewayAdapter`), que detém propriedade exclusiva sobre `bin/carina-go`, conexões SNMP locais do `HardwareConnectionManager` e ingestão de telemetria do `EVPService`.
- **Processos Espelho Remotos (`CARINA_GATEWAY_ROLE=remote`):** Definido em [`carina.py`](../../carina.py), [`src/main.py`](../../src/main.py) (`AI_Process`) e [`dashboard_worker.py`](../../src/sds/dashboard_worker.py). Os processos remotos sincronizam o status espelhado via IPC (`RemoteHardwareDriverProxy` por meio de [`remote_proxy_synchronizer.py`](../../src/drivers/remote_proxy_synchronizer.py)) e encaminham ações/preempções (`ai_hardware_cmd`, `ai_evp_preempt`, `set_hardware_connection`) através de [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Telemetria de Hardware em Malha Fechada (`HardwareTelemetrySynchronizer`):** Dentro do loop de IA, [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) e [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) decodificam máscaras de bits reais de NTCIP 1202 / UTMC2 (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) para índices de estágio 0-based do SUMO, permitindo controle verdadeiro em malha fechada e reconciliação de handover do F.E.N.I.X.

---

## 2. Arquitetura Avançada de Deep Learning

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │   Detecta Nós do Mapa (N) -> Dimensão Latente (32/64/128/256), Heads    │
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │     LOCAL AGENT (PPO)       │           │   STRATEGIST AGENT (GRAPH)  │
     │  Backbone TCN Tático        │           │   Coordenador ST-GATv2 Lite │
     │  (Atuação Sub-segundo)      │◄──────────┤   (Ondas Verdes Arteriais)  │
     └──────────────┬──────────────┘Vetor Ctx  └──────────────┬──────────────┘
                    │                                         │
                    │ Ação Proposta                           │ Contexto de Rede
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │  Escudo Neuro-Simbólico de Segurança, Prevenção de Spillback e Veto   │
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 Módulo ST-GATv2 Lite (`src/models/st_gatv2_lite.py` & `src/engine/strategic_coordinator.py`)
- **Propósito:** Sincronização espacial de "Ondas Verdes" arteriais entre cruzamentos vizinhos no grafo viário urbano usando `TemporalConvNetLite` (`GroupNorm(1, C)` + `SiLU` + `TemporalAttentionPool`) seguido por duas camadas residuais `GATv2Conv`.
- **Cabeças Auxiliares Online & CTDE:** Inclui uma cabeça auxiliar de previsão de próximo passo (`pred_head`) e uma cabeça de valor global cooperativo (`global_critic_head`). [`StrategicCoordinator`](../../src/engine/strategic_coordinator.py) agrega sequências de nós via chamadas não-mutantes [`StateExtractor.peek_state()`](../../src/engine/state_extractor.py) para que leituras secundárias do grafo nunca corrompam as EMAs do `HistoricalAggregator`.
- **Coordenação Descentralizada:** O Strategist calcula periodicamente o tensor de contexto espaço-temporal da rede e o entrega aos agentes locais via gating residual tanh (`PAEStateAugmentor`), permitindo ondas verdes emergentes sem comandos centralizados de ponto único de falha.

### 2.2 Autoencoder Preditivo Universal iTransformer Condicionado à Ação (`src/models/pae.py`)
- **Propósito:** Modelo de mundo físico compartilhado de alta capacidade que projeta dinâmicas espaço-temporais futuras ($t + \Delta t$) entre topologias heterogêneas de cruzamentos.
- **Arquitetura iTransformer & Incerteza:** Emprega RevIN por variável + embedding de escala `[mean, std]`, camadas encoder Transformer invertidas sobre as variáveis de sensores, pooling latente por atenção cruzada com `key_padding_mask` (`valid_dims`) para que faixas com zero-padding nunca contaminem vetores latentes, condicionamento binário à ação (`0 = ADVANCE`, `1 = KEEP`) e estimação de incerteza heteroscedástica (`decode_with_uncertainty -> (mean, log_var)`), com aquecimento opcional via `torch.compile` (`torch_compile_helper.py`).
- **Codificação em Lote de Passagem Única:** Executado uma vez por passo de simulação em todas as interseções via [`BatchedPAEEncoder`](../../src/engine/batched_pae_encoder.py) e reutilizado no [`PPOOptimizer`](../../src/optimizer/ppo_optimizer.py) ao longo das épocas de rollout por meio de `precomputed_latents`.

### 2.3 Vetorização Tática & Segurança Distribucional do Guardião (`src/engine/`, `src/safety/`)
- **Backbone TCN Causal Unificado (`src/models/tcn_backbone.py`):** Substitui o obsoleto `weight_norm` por `TemporalConv1d`, `GroupNorm(1, C)` causal por canal, `SiLU`, inicialização ortogonal e `TemporalAttentionPool`. `ActorCriticNet` emite logits FP32 brutos (`forward_logits`) mascarados diretamente pelo [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py) (impondo entreverdes de amarelo/vermelho total, verde mínimo e verde máximo).
- **Inferência Homogênea com `torch.vmap` (`src/engine/fleet_batch_inferencer.py`):** Agrupa `LocalAgent`s por assinatura arquitetural e executa passagens forward vetorizadas via `torch.func.stack_module_state` + `torch.vmap`, empacotando escalares em buffers NumPy na CPU (`last_cpu_decisions`) e usando GAE em NumPy no host no `PPOOptimizer`, além de `ReplayMemory` / `StateReplayMemory` residentes na CPU (`pin_memory`, cache `_max_priority` em $O(1)$, `push_batch`).
- **Guardião QR-D3QN Calibrado & Noisy-OR (`src/safety/`):** `D3QN_TCN` modela `num_quantiles = 32` por ação binária para risco de cauda $\text{CVaR}_{0.20}$. [`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py) normaliza a saturação das vias de entrada pelas capacidades reais em veículos e projeta sobre o horizonte de entreverde $H = \text{yellow} + \text{all\_red}$; [`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py) realiza calibração logística ajustada por $F_2$-score e **fusão Noisy-OR** não-compensatória. [`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) treina o Guardião exclusivamente durante `Maturity.CHILD`, executando em seguida `freeze_for_deployment()` na graduação e persistindo `guardian_{tl_id}.pth` via [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py).

### 2.4 Auto-Escalonador Topológico $O(1)$ (`src/utils/topo_scaler.py`)
- **Escalonamento Algorítmico:** Detecta automaticamente a densidade da rede ($N$ interseções) e ajusta as dimensões neurais em potências de 2 otimizadas para TensorCores NVIDIA:
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$ (ex: Malha Metropolitana de Londrina)
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$ (Grandes Megalópoles)

### 2.5 Aceleração Universal AMP & TensorCore
- Todos os passos forward de redes neurais são envelopados em `torch.amp.autocast`, habilitando aceleração nativa FP16/TF32 em TensorCores NVIDIA e restringindo o consumo total de VRAM a apenas **~20 MB** para os modelos centrais.

---

## 3. Armazenamento Delta Assíncrono & Pooling de Conexões

O CARINA implementa um motor de persistência assíncrono com **Compressão Delta por Run-Length Encoding** e pool de conexões thread-safe em PostgreSQL e SQLite:
- **`step_decisions`**: Registra sugestões, vetos de segurança e cronômetros via [`StepDecisionWorker`](../../src/database/step_decision_worker.py) em filas de RAM não-bloqueantes ($< 0,001\text{ ms}$ de sobrecarga).
- **`edge_dictionary`**: Mapeia nomes extensos de vias para inteiros de 4 bytes para indexação ultracompacta.
- **Pool de Conexões & Pragmas (`src/database/connection_pool.py`):** Provê `PostgresConnectionPool` (`psycopg2.pool.ThreadedConnectionPool`, `minconn=1, maxconn=16`), gerenciamento determinístico de contexto `db_transaction`, tuning SQLite WAL (`busy_timeout=30000`, `synchronous=NORMAL`, `temp_store=MEMORY`, `journal_mode=WAL`), opção `enable_step_worker=False` para workers somente-leitura (`XaiWorker`), consultas parametrizadas `make_interval(...)` e expurgo automático de telemetria EVP após 168 horas.
- **Redução de Espaço:** Redução global de **97,9% no volume de armazenamento** (~380 MB/dia para 200 cruzamentos em malha metropolitana).

Para especificações detalhadas de tabelas e esquemas SQL, consulte [Arquitetura de Banco de Dados & Esquemas](database_and_schemas.md).

---

## 4. Arquitetura Modular de Configurações (`src/settings/`)

Em conformidade com os princípios de **Responsabilidade Única** e **Segregação de Interface** (SOLID), o gerenciamento de configurações do CARINA é decomposto em componentes testáveis e desacoplados:

```text
       ┌────────────────────────────────────────────────────────┐
       │               SettingsService (Orquestrador)           │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(Validação e   │     │& Write       │ │(I/O arquivo    │ │(Segredos .env        │
│ Mapa Seções)  │     │(Interfaces)  │ │ settings.ini)  │ │ App 12-Factor)       │
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ Fachada de Compatibilidade Retroativa
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`):** Registro autoritativo definindo mapeamentos chave-seção (incluindo chaves gRPC TLS/token em `[SYNAPSE]` e chaves TLS/CORS/porta em `[REMOTE_GATEWAY]`), valores padrão de fallback e regras de validação de tipo.
- **`IniFileStorage` (`src/settings/ini_storage.py`):** Gerencia leitura e gravação persistente no arquivo `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** Resolve segredos de infraestrutura sensíveis a partir de variáveis de ambiente no `.env` (incluindo `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN`, `CARINA_GATEWAY_TLS_*`, `CARINA_GATEWAY_PORT` e `CARINA_TRAP_PORT`).
- **`SettingsService` (`src/settings/service.py`):** Serviço central orquestrando recuperação, validação e serialização.
- **`SettingsManager` (`src/utils/settings_manager.py`):** Fachada retrocompatível garantindo zero regressões em chamadas legadas.
- **Protocolos SOLID (`src/interfaces/`):** Interfaces segregadas entre `controller.py`, `drivers.py`, `engine.py` e `repositories.py` desacoplando camadas de coordenação, gateway, driver, PAE, mascaramento de ações e persistência.

---

## 5. Arquitetura Polimórfica de Monitoramento & Transportes (`src/transports/`)

O CARINA conta com uma **camada polimórfica de transporte de telemetria e incidentes** suportando corretores MQTT locais, webhooks remotos, APIs Cloud REST e soluções de tunelamento (ex: Ngrok):

```text
IncidentReporter / TelemetryLoop
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (Fachada Singleton)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (Fábrica com Resolução Automática de Endpoints)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│ (Broker Local / de Rede)  │             │ (API REST / Nuvem / Ngrok)│
│ - Host:Port (ex: :1883)   │             │ - http:// ou https://     │
│ - Telemetria QoS 0/1      │             │ - Sessão HTTP Persistente │
│ - Tópicos: noxfort/telem/ │             │ - Retry com backoff expon.│
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 Abstração de Transporte (`BaseMonitorTransport`)
Define o contrato rigoroso para todos os exportadores de telemetria externa:
- `setup()`: Configura endpoints, timeouts e credenciais.
- `ensure_connected()`: Estabelece ou valida a conectividade da sessão.
- `publish(topic, payload)`: Transmite cargas JSON assincronamente ou em threads de trabalho dedicadas.
- `disconnect()`: Descarrega buffers pendentes e encerra a conexão de forma limpa.

### 5.2 Resolução Automática de Endpoints (`endpoint_resolver.py`)
Classifica inteligentemente os endpoints de destino sem requerer configuração explícita de protocolo:
- URLs iniciando com `http://` ou `https://` (ou contendo `ngrok`, `run.app` ou `/api/`) instanciam `MonitorHttpTransport`.
- Strings comuns de hostname/IP (`localhost`, `10.0.0.1`, `broker:1883`) instanciam `MonitorMqttTransport`.

### 5.3 Deduplicação de Incidentes & Filtro de Alertas (`src/drivers/`)
- [`IncidentReporter`](../../src/drivers/incident_reporter.py) transmite mudanças de estado de conexão e falhas de controladores para ferramentas de monitoramento externo.
- [`IncidentFilter`](../../src/drivers/incident_filter.py) suprime enxames de notificações persistindo hashes de incidentes ativos com debounce temporal em `.carina_incident_filter_cache.json`.

---

## 6. Gateway de Hardware Industrial em Go (`src_go/`)

Para atingir confiabilidade industrial, determinismo de rede em sub-milissegundos e zero contenção de GIL em implantações de campo, o CARINA delega toda a comunicação de rede com controladores de tráfego físico (portas UDP 161 e 162) a um **Gateway compilado em Go** dedicado (`bin/carina-go` compilado a partir de `src_go/`):

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │   [Synapse Perception]  <-- gRPC (50051) -->  [Câmera] │
       │            │                                           │
       │      [AI Engine / NN]                                  │
       │            │                                           │
       │     [ActionSupervisor]                                 │
       │            │                                           │
       │ [HardwareConnectionManager] (Orquestrador Python)      │
       │            │                                           │
       │    [GoGatewayClient] (Gerenciador de Pipes)            │
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout (JSON Delimitado por Linha)
                    │ ZERO PORTAS DE REDE ABERTAS NO HOST
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │          CARINA HARDWARE GATEWAY (Daemon em Go)        │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [Scanner NDJSON IPC & Gravador Concorrente]       │
       │  +-- [Registro de Conexões HardwareManager]            │
       │  +-- [Fail-Safe Atômico em caso de EOF / SIGPIPE]      │
       │  +-- [Motor de Heartbeat: time.Ticker por cruzamento]  │
       │  +-- [Despachantes de Protocolo NTCIP 1202 & UTMC2]    │
       │  +-- [Pool de Clientes GoSNMP (UDP 161)]               │
       │  +-- [Servidor TrapListener (UDP 162)]                 │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Traps)
                            ▼                  ▼
                    [Controlador Real]   [Controlador Real] ...
```

### 6.1 Propriedades Arquiteturais Centrais
- **Propriedade em Processo Único & Zero Portas de Controle Locais:** Apenas o `CentralController` (`CARINA_GATEWAY_ROLE=owner`) inicializa `bin/carina-go`. A ligação de controle entre Python e Go opera estritamente via pipes anônimos do sistema operacional (`pipe(2)` NDJSON `stdin`/`stdout`), enquanto `AI_Process` e `UI` espelham o estado por meio de [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py).
- **NTCIP 1202, UTMC2 & SNMPv3 USM:** Implementa OIDs canônicos NTCIP 1202 (`.4.1.*` status / `.5.1.*` controle), OIDs UTMC2 de demanda/estágio, decodificação de inteiros e octet-strings `GetBitmask` (`src_go/pkg/snmp/codec.go`), SNMPv3 USM completo (`NoAuthNoPriv`, `AuthNoPriv`, `AuthPriv`) e sobrescritas de OIDs por interseção via `config_path` persistidas em `hardware_controller_connections.snmp_config` e planilhas CSV.
- **Decodificador Binário de Traps SNMP & Guarda de Entreverdes:** [`snmp_decoder.go`](../../src_go/pkg/traplistener/snmp_decoder.go) decodifica Traps e Informs binários SNMPv1/v2c/v3, enquanto [`HardwareStageActuator`](../../src/drivers/hardware_stage_actuator.py) ignora retenções conflitantes durante intervalos de entreverdes amarelo/vermelho total.
- **Fail-Safe Atômico & Recuperação:** Em `EOF`/`SIGPIPE`, o Go invoca `ShutdownAll()` via SNMP; durante timeouts de execução do Watchdog, `EmergencyReleaseControlAll()` pausa os heartbeats e libera as retenções mantendo drivers/trap listener ativos para que `resume_control` (`ResumeControlAll()`) recupere a operação sem reconectar sockets.
- **Adaptador Transparente (`GoTrafficDriverProxy` & `RemoteHardwareDriverProxy`):** Ambos os proxies locais e remotos implementam `BaseTrafficDriver` (LSP), mantendo a orquestração de hardware transparente para `ActionSupervisor` e `StepProcessor`.

---

## 7. Subsistema de Auto-Cura F.E.N.I.X. & Supervisão de Processos (`src/fenix/`)

O CARINA integra o subsistema **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) para garantir auto-recuperação autônoma contínua 24/7 para o motor de inferência de IA:

```text
       ┌────────────────────────────────────────────────────────┐
       │                Monitor de Saúde Watchdog               │
       └───────────────────────────┬────────────────────────────┘
                                   │ Timeout / Perda de Heartbeat
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            FenixSupervisor (Orquestrador)              │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- Backoff em janela desliz. │ │- Ciclo de vida subprocess│
       │- Limitador de quota max    │ │- SIGTERM / SIGKILL      │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ Ressurreição
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- Telemetria FROZEN_SYNC │
                                      │- FenixStageDispatcher   │
                                      │- Transição sem colisões │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`) & `fenix_supervision_loop.py`:** Coordena encerramento de processos, backoff de recuperação, ressurreição de filhos e confirmação `HANDOVER_COMPLETE`.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** Computa backoffs exponenciais e impõe limites de reinício para prevenir tempestades de reinicializações cíclicas.
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** Gerenciamento de baixo nível garantindo isolamento determinístico de processos e encerramento limpo via SIGTERM com fallback para SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`) & `FenixStageDispatcher` (`src/controller/fenix_stage_dispatcher.py`):** Mantém o motor de IA ressuscitado em modo `FROZEN_SYNC`, consulta os estágios reais dos controladores via `HardwareTelemetryDecoder` e dispara `fenix_post_resurrection` -> `fenix_handover_complete` apenas em fronteiras de fase livres de colisão.

---

## 8. Ciclo de Vida do Agente, PBT Intra-Fase & Motor de Promoção (`src/maturity/`, `src/promotion/`, `src/core/`)

O CARINA estrutura as políticas de aprendizado por reforço como um organismo em desenvolvimento por currículo estagiado de 3 fases:

```text
  ┌──────────────────┐       Queda de Entropia & Pacing   ┌──────────────────┐      Entropia & Margem Fluida (delta*)    ┌──────────────────┐
  │  FASE CRIANÇA    │ ─────────────────────────────────> │ FASE ADOLESCENTE │ ───────────────────────────────────────>  │   FASE ADULTA    │
  │  (Shadow Mode)   │                                    │(Autonomia Off-Pk)│                                           │(Autonomia Total) │
  └────────┬─────────┘                                    └────────┬─────────┘                                           └────────┬─────────┘
           │                                                       │                                                              │
           ▼                                                       ▼                                                              ▼
  [Blindado contra PBT]                                   [PBT Intra-Fase]                                              [PBT Intra-Fase]
  [Observa Fluidodinâmica]                                (Apenas TEEN <-> TEEN)                                        (Apenas ADULT <-> ADULT)
  [Piso Mínimo 1 Semana]                                  [Modo Sombra nos Picos]                                       [Controle Ativo 24/7]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`):** Fachada e Application Service orquestrador do ciclo de vida de maturidade, apoiado pela entidade rica `AgentMaturity`, `MaturityConfig` e `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`):** Executa o **PBT Intra-Fase**. Os agentes clonam pesos neurais e sofrem mutação apenas dentro de sua coorte geracional (`TEEN` com `TEEN`, `ADULT` com `ADULT`), enquanto agentes `CHILD` permanecem completamente blindados. Inclui validação de tensores para evitar falhas em cruzamentos com topologias heterogêneas.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`):** Avalia rigorosamente a entropia de Shannon da política, durações mínimas de fase e metas de performance.
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`):** Dimensiona dinamicamente a contagem de passos de cada episódio a partir da topologia viária física (unificando vias de mão dupla, excluindo conexões internas `:` e aplicando relaxamento sub-linear $\sqrt{N}$ e $D_{\text{km}}$), calculando o piso inviolável de 1 semana completa ($E_{\text{semana}}$ episódios a $\Delta t = 250\text{ ms}$).
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`):** Rastreia e persiste atomicamente a cobertura das 168 faixas horárias reais da semana ($7\text{ dias} \times 24\text{ horas}$), permitindo pausas e reinicializações de processos sem perda do histórico de maturação.
- **`ActionAuthorizer` (`src/core/action_authorizer.py`):** Restringe fisicamente a atuação do estágio `TEEN`, forçando modo sombra durante horários de pico urbanos clássicos (06:30-09:00 e 17:00-19:30 nos dias úteis) ou conforme grade dinâmica enviada pelo Synapse.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`):** Orquestra o pacing integrando o `EpisodeStepCalculator` e aplicando o piso inviolável de segurança ($t_{\min} = \max(E_{\text{semana}}, \text{configuração})$).
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`):** Calcula dinamicamente a margem exigida para graduação $\delta^* \in [3.0\%, 25.0\%]$ utilizando telemetria empírica de velocidade e ocupação coletada durante a infância no `synapse_fluid_dynamics`.

---

## 9. Subsistema de Balanceamento Físico de Recompensas (`src/engine/reward_weights_calculator.py`)

Para eliminar o abismo de grandezas onde o tempo de espera acumulado supera o incentivo de fluxo de veículos por ordens de magnitude, o CARINA equilibra a recompensa com base no tempo de travessia livre da engenharia de tráfego (HCM):

$$\tau = \frac{\bar{L}_{\text{vias}}}{\bar{v}_{\text{limite}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`):** Calcula os pesos normalizados ao carregar a topologia da malha (`TopologyManager.load_topology`).
- **`RewardCalculator` (`src/engine/reward_calculator.py`):** Injeta os pesos calibrados via `set_reward_weights`, garantindo que descarregar veículos tenha o mesmo impacto na gradiente do PPO que a redução do tempo de fila.

---

## 10. Subsistema de Agendamento de Amarelo Intermitente Noturno (`src/controller/yellow_schedule_manager.py`)

Para conformidade com o Código de Trânsito Brasileiro (CTB) e segurança em horários de madrugada com volume residual de veículos, o CARINA inclui um gerenciador autônomo de intermitência noturna:
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`):** Avalia janelas temporais configuradas (ex: 23:00 às 05:00), colocando os semáforos automaticamente em alerta intermitente ou retomando a IA adaptativa nas fronteiras do agendamento.
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`):** Interface permitindo habilitar/desabilitar a regra, configurar horários de início/fim e aplicar a semáforos específicos ou a toda a malha municipal.

---

## 11. Subsistema de Preempção de Veículos de Emergência (EVP) (`src/evp/`, `src_go/evp_go/`)

Para conceder Corredores Verdes imediatos para viaturas de socorro (**SAMU**, **Corpo de Bombeiros** e **Polícia**) em conformidade com a Resolução CONTRAN nº 960 e Art. 29 do CTB, o CARINA incorpora um subsistema dedicado de preempção:

```text
 Antena GPS / Transponder      Go Web Gateway (:2201 / :8085)        EVPService (src/evp/)
           │                             │                                   │
           │── POST /api/v1/evp/telemetry ─>│                                   │
           │   (HTTP 204 No Content)     │── NDJSON / Stream em Memória ────>│
           │                             │                                   ├── Cinemática (Haversine WGS84)
           │                             │                                   ├── Entrada no Gate (60m <= d <= 160m)
           │                             │                                   └── Verificação de Sirene Ativa
           │                             │                                           │
           │                             │                                           ▼
           │                             │                                 SafetyAuditor (Regra nº 0)
           │                             │                                 (Entreverdes -> ACTION_HOLD)
           │                             │                                           │
           │<───── Corredor Verde ───────┼── SNMP ascPhaseHold (Go Dispatcher) <─────┘
```

- **Gatilho de Dois Fatores:** A preempção exige entrada simultânea no gate de aproximação ($60\text{ m} \le d \le 160\text{ m}$) E alarme sonoro ativo (`siren_active = True`).
- **Interceptação Prioritária no SafetyAuditor:** A Regra nº 0 intercepta as ações propostas, respeita intervalos de entreverdes (amarelo e vermelho total) e sustenta a fase verde (`ACTION_HOLD = 1`).
- **Limite de Watchdog CONTRAN ($45\text{ s}$):** Aborta a retenção incondicionalmente após 45 segundos para prevenir travamento cruzado de vias arteriais.
- **Checkout Imediato:** Assim que a viatura cruza a linha de retenção ($d \le 15\text{ m}$), a preempção é liberada imediatamente.

Para especificações técnicas completas, consulte [Preempção de Veículos de Emergência (EVP)](evp_and_preemption.md).

---

## 12. Arquitetura Web da Central de Controle Operacional (CCO) & Segurança de Transporte (`src_go/web_gateway/`, `src_tsx/src_cco/`)

O CARINA disponibiliza uma central de operações web segura para videowalls municipais e monitoramento remoto:
- **`WebGatewayServer` (`src_go/web_gateway/server.go`, `auth.go`):** Servidor HTTP/HTTPS em Go embutido rodando na porta 2201 (`CARINA_GATEWAY_PORT`). Assume `gateway_enabled=False` por padrão (retornando `503 Service Unavailable` até ser habilitado), impõe autenticação em tempo constante por token Bearer/header (`CARINA_CCO_AUTH_TOKEN`, `CARINA_EVP_AUTH_TOKEN`), origens CORS explícitas (`CARINA_CCO_ALLOWED_ORIGIN`), terminação TLS (`CARINA_GATEWAY_TLS_CERT`/`KEY`), streaming SSE (`/cco/stream`), endpoints de topologia (`/cco/topology`) e tunelamento via Tailscale Funnel.
- **`CCOBroadcastClient` (`src/sds/cco_broadcast_client.py`, `cco_tls_transport.py`):** Publicador não-bloqueante *latest-wins* que encaminha atualizações do SDS para `/cco/broadcast` com autenticação `X-CCO-Token`, verificação TLS de CA e pinning opcional de certificado folha SHA-256 (`PinnedHTTPSConnection`).
- **`Segurança Synapse gRPC` (`src/communication/grpc_security.py`):** Suporta TLS/mTLS (`CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_REQUIRE_CLIENT_CERT`) e `BearerTokenServerInterceptor` (`CARINA_GRPC_AUTH_TOKEN`) na porta `:50051`.
- **`Aplicação Web CCO` (`src_tsx/src_cco/`):** Dashboard moderno em React 18, TypeScript, Tailwind CSS, renderizador de camadas vetoriais SVG e Apache ECharts com animações CSS exclusivas no compositor (`transform`/`opacity`), referências de pan/zoom guiadas por `requestAnimationFrame`, diffing de view-model por igualdade rasa e pausa de temporizadores quando `document.hidden` é verdadeiro.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
