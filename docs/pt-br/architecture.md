---
tags: [arquitetura, nucleo, sistema, gatv2, pae, pbt, amp, multiprocessamento]
aliases: [Arquitetura do Sistema, Blueprint Multiprocesso, Visão Geral do Sistema]
---

# 🏛️ CARINA: Blueprint do Sistema e Arquitetura de Multiprocessamento

Este documento especifica a arquitetura interna de engenharia do ecossistema CARINA. Ele detalha os 8 microsserviços concorrentes em processos do sistema operacional, a topologia canônica de redes neurais profundas (LocalAgent PPO-TCN, GuardianAgent D3QN e StrategistAgent ST-GATv2 Lite), o `TopologicalScaler`, os drivers de controladores físicos e o motor assíncrono de persistência com compressão delta no PostgreSQL.

⬅️ [Central Master de Documentação](carina_moc.md) | 🚨 [Preempção de Emergência (EVP)](evp_and_preemption.md) | 🚦 [Controladores de Hardware](hardware_drivers.md) | 🧠 [Notas de Pesquisa & Formulações](research_notes.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Modelo de Concorrência de Microsserviços Multiprocesso

O Global Interpreter Lock (GIL) do Python impede inferência de IA intensiva em CPU e operações pesadas de I/O em verdadeiro paralelismo multithread. Para garantir latência de atuação em sub-milissegundos, o CARINA implementa um **modelo de microsserviços multiprocesso** orquestrado por [`carina.py`](../../carina.py) e [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py), combinado com um **Gateway Industrial de Hardware & Web em Go** (`bin/carina-go`):

```mermaid
graph TD
    Launcher[carina.py / Bandeja de Sistema] -->|Inicializa e Monitora| PM[ProcessManager]

    PM --> CC[1. Processo CentralController]
    PM --> AI[2. Motor AI_Process]
    PM --> WD[3. Processo Watchdog]
    PM --> SDS[4. DashboardService SDS]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Motor MFD_Worker]

    CC <-->|IPC Pipe| AI
    CC -->|Fila wd (Heartbeats)| WD
    AI -->|Fila db| DB
    CC -->|Fila sds| SDS
    CC -->|Fila sas| SAS
    CC -->|Fila mfd_trigger| MFD
    MFD -->|Fila mfd_results| CC
    SAS -->|Fila sas_results| CC
    XAI -->|Logs HFT em Disco| AI

    CC <-->|Tubo Anônimo Stdin/Stdout NDJSON| GW[Go Gateway carina-go]
    GW --> NTCIP[Controladores NTCIP / UTMC UDP 161]
    GW --> WebGW[Go Web Gateway Porta 2201 / Tailscale]
    WebGW --> CCO[Videowall CCO React/TSX src_tsx]
    WebGW <--|POST 204 Telemetria| EVP[Antenas GPS EVP Porta 8085]
```

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

### 2.1 Módulo ST-GATv2 Lite (`src/models/st_gatv2_lite.py`)
- **Propósito:** Sincronização espacial de "Ondas Verdes" arteriais entre cruzamentos vizinhos no grafo viário urbano.
- **Ponderação Dinâmica:** Embora a topologia física seja estática, os coeficientes dinâmicos de atenção espacial $\alpha_{ij}(t)$ são recalculados em tempo real com base nas densidades de veículos e gradientes de velocidade.
- **Coordenação Descentralizada:** O Strategist calcula periodicamente o tensor de contexto espaço-temporal da rede e o entrega aos agentes locais e guardiões, permitindo ondas verdes emergentes sem comandos centralizados imperativos de ponto único de falha.

### 2.2 Autoencoder Preditivo Universal (`src/models/pae.py`)
- **Propósito:** Motor de representação física de alta capacidade compartilhada, comprimindo dinâmicas temporais sequenciais em espaços latentes invariantes ($Z \in \mathbb{R}^{16\dots 128}$).
- **Enriquecimento Direcionado:** Fornece representações latentes temporais compactas tanto para as decisões de política do LocalAgent quanto para a auditoria de risco de spillback do GuardianAgent.

### 2.3 Auto-Escalonador Topológico $O(1)$ (`src/utils/topo_scaler.py`)
- **Escalonamento Algorítmico:** Detecta automaticamente a densidade da rede ($N$ interseções) e ajusta as dimensões neurais em potências de 2 otimizadas para TensorCores NVIDIA:
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$ (ex: Malha Metropolitana de Londrina)
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$ (Grandes Megalópoles)

### 2.4 Aceleração Universal AMP & TensorCore
- Todos os passos forward de redes neurais são envelopados em `torch.amp.autocast`, habilitando aceleração nativa FP16/TF32 em TensorCores NVIDIA e restringindo o consumo total de VRAM a apenas **~20 MB** para os modelos centrais.

---

## 3. Armazenamento Delta Assíncrono no PostgreSQL

O CARINA implementa um motor de persistência assíncrono com **Compressão Delta por Run-Length Encoding** no PostgreSQL:
- **`step_decisions`**: Registra sugestões, vetos de segurança e cronômetros via [`StepDecisionWorker`](../../src/database/step_decision_worker.py) em filas de RAM não-bloqueantes ($< 0,001\text{ ms}$ de sobrecarga).
- **`edge_dictionary`**: Mapeia nomes extensos de vias para inteiros de 4 bytes para indexação ultracompacta.
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

- **`SettingsSchema` (`src/settings/schema.py`):** Registro autoritativo definindo mapeamentos chave-seção, valores padrão de fallback e regras de validação de tipo.
- **`IniFileStorage` (`src/settings/ini_storage.py`):** Gerencia leitura e gravação persistente no arquivo `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** Resolve segredos de infraestrutura sensíveis a partir de variáveis de ambiente no `.env`.
- **`SettingsService` (`src/settings/service.py`):** Serviço central orquestrando recuperação, validação e serialização.
- **`SettingsManager` (`src/utils/settings_manager.py`):** Fachada retrocompatível garantindo zero regressões em chamadas legadas.

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
- **Zero Portas Abertas no Host:** A ligação de controle entre Python e Go roda exclusivamente através de pipes anônimos padrão do sistema operacional (`pipe(2)` nos buffers do kernel). Nenhuma porta de localhost, socket ou serviço HTTP é exposto.
- **Fail-Safe de Segurança Atômico:** Caso o processo de IA em Python sofra uma queda abrupta, o kernel fecha o pipe. O binário em Go detecta `EOF` em `os.Stdin` em microssegundos e imediatamente dispara `EmergencyReleaseControlAll()` via SNMP, liberando remotamente as retenções de fase e devolvendo os controladores para seus planos locais fixos.
- **Zero Contenção de GIL:** Goroutines executam sondagem concorrente, heartbeats de keepalive a cada 2,0s e escuta de traps UDP 162 de forma totalmente independente das operações tensoriais pesadas do PyTorch em Python.
- **Adaptador Transparente (`GoTrafficDriverProxy`):** Adere ao Princípio de Substituição de Liskov (LSP) implementando `BaseTrafficDriver`, tornando o gateway Go 100% transparente para todo o restante da base de código do CARINA.

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
                                      │- Handshake de fronteira │
                                      │- Transição sem colisões │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`):** Coordena encerramento de processos, backoff de recuperação, ressurreição de filhos e reconciliação de estado.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** Computa backoffs exponenciais e impõe limites de reinício para prevenir tempestades de reinicializações cíclicas.
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** Gerenciamento de baixo nível garantindo isolamento determinístico de processos e encerramento limpo via SIGTERM com fallback para SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`):** Garante que o motor de IA ressuscitado opere em modo `FROZEN_SYNC` e só assuma controle da atuação semafórica em fronteiras limpas de estágio, quando os controladores de rua transitam naturalmente de ciclo.

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

## 12. Arquitetura Web da Central de Controle Operacional (CCO) (`src_go/web_gateway/`, `src_tsx/src_cco/`)

O CARINA disponibiliza uma central de operações web para videowalls municipais e monitoramento remoto:
- **`WebGatewayServer` (`src_go/web_gateway/server.go`):** Servidor HTTP Go embutido rodando na porta 2201 fornecendo streaming de eventos via SSE (`/cco/stream`), endpoints de topologia (`/cco/topology`) e tunelamento criptografado via Tailscale Funnel.
- **`Aplicação Web CCO` (`src_tsx/src_cco/`):** Dashboard moderno em React 18, TypeScript, Tailwind CSS, renderizador de camadas vetoriais SVG e Apache ECharts exibindo posições de veículos em tempo real, tempos semafóricos e alertas de preempção.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
