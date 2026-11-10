---
tags: [moc, hub, docs, obsidian, carina, indice]
aliases: [CARINA MOC, Central Master de Documentação, Índice de Documentação, Vault de Conhecimento]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA: Central Master de Documentação Técnica (MOC)
### Índice Central & Vault de Conhecimento da Arquitetura Multiagente
*Noxfort Systems — A State Of Art Company*

</div>

Bem-vindo à biblioteca técnica do **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture). Projetado como um ecossistema de Aprendizado por Reforço Profundo de alta frequência e massivamente concorrente para controle semafórico adaptativo em tempo real, o CARINA conecta IA neuro-simbólica de alto nível, atuação física de campo de sub-milissegundos via gRPC e isolamento estrito de múltiplos processos no sistema operacional.

Este índice mestre de documentação fornece cobertura técnica profunda para desenvolvedores de núcleo, pesquisadores acadêmicos, engenheiros de tráfego municipais e integradores de sistemas. É 100% compatível tanto com o **GitHub** quanto com o **[Obsidian](https://obsidian.md/)**.

---

## 🗺️ Mapa da Base de Código & Hierarquia de Diretórios

```text
CARINA_CORE/
├── carina.py                   # Orquestrador Mestre (SingleInstanceLock, ProcessManager, UI/Bandeja)
├── ARCHITECTURE.md             # Blueprint de Arquitetura com 8 Processos e Topologia IPC
├── pyproject.toml              # Toolchain de compilação e metadados do projeto
├── requirements.txt            # Dependências de execução em Python
├── .env.example                # Variáveis de ambiente e credenciais (Padrão 12-Factor)
│
├── config/                     # Sistemas de Configuração
│   ├── settings.ini            # Parâmetros globais (IA, PBT, Watchdog, MFD, Logging)
│   ├── database/               # Esquemas e queries SQL dinâmicas (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Regras de segurança e consistência semântica (safety_rules.json, semantic_rules.json)
│   └── templates/              # Templates multilíngues de laudos, MFD, SAS e XAI
│
├── packaging/                  # Empacotamento Hermético Debian & Especificações
│   ├── Dockerfile.build        # Construtor hermético multi-estágio (Node, Go, Python, dpkg-deb)
│   └── deb/                    # Arquivos de controle Debian, unidades systemd & scripts pós-instalação
│
├── scripts/                    # Scripts de Compilação, Automação & Migrações
│   └── build_deb.sh            # Gerador de pacotes Debian containerizado
│
├── proto/                      # Especificações do Protocolo gRPC
│   └── synapse_hft.proto       # Definições Protobuf para telemetria de alta frequência e atuação
│
├── docs/                       # Vault Geral de Documentação Técnica
│   ├── CARINA_MOC.md           # Central Master de Documentação (Este Arquivo)
│   ├── index.md                # Portal de Entrada MkDocs
│   ├── ARCHITECTURE.md         # Blueprint de Arquitetura com 8 Processos e Topologia IPC
│   ├── EVP_AND_PREEMPTION.md   # Preempção de Veículos de Emergência, Go Web Gateway & CCO
│   ├── API_REFERENCE.md        # Especificação gRPC Synapse HFT e Esquemas de Filas IPC
│   ├── RESEARCH_NOTES.md       # Formulações Matemáticas: PPO-TCN, PAE, GATv2 e DA SILVA
│   ├── HARDWARE_DRIVERS.md     # Controladores Físicos: NTCIP 1202, UTMC2 e Integração SNMP
│   ├── SAFETY_AND_WATCHDOG.md  # Firewall de Segurança Guardian, Regras de Veto e Watchdog
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # Justificativas Semafóricas MUTCD / FHWA 1, 2, 3, 4
│   ├── MFD_AND_ANALYTICS.md    # Diagrama Fundamental Macroscópico e Dinâmica de Densidade
│   ├── DATABASE_AND_SCHEMAS.md # Camada de Persistência, Armazenamento Delta Assíncrono e SQL
│   ├── XAI_AND_SAS.md          # IA Explicável, Gradientes Integrados Captum e Analítica SAS
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # Construtor Modular Word ABNT (.docx) e Fórmulas OMML
│   ├── SLM_AND_LOCAL_LLM.md    # Integração Local de LLM Offline (Qwen3.5 2B / llama.cpp)
│   ├── UI_AND_DASHBOARD.md     # Interface Flet Desktop, Visão de Planejamento e SDS
│   ├── RENDERING_AND_HEATMAPS.md # Renderização de Mapas Vetoriais e Interpolação de Heatmaps
│   ├── SECURITY_AND_AUTH.md    # Contas de Usuário, Hashing PBKDF2 HMAC-SHA256 e Bloqueio de Brute-Force
│   ├── DEVELOPER_GUIDES.md     # Configuração de Ambiente, Hierarquia de Agentes e Configurações
│   ├── TESTING.md              # Suíte Pytest, Mocks de Controladores e Validação de Cobertura
│   └── DEPLOYMENT_AND_PACKAGING.md # Builds Docker, Daemons Systemd e Pacotes Debian
│
├── bin/                        # Binários nativos compilados (carina-go)
├── src_go/                     # Gateway de Hardware e Web em Go (NTCIP, UTMC, EVP, Web Gateway)
│   ├── cmd/gateway/            # Ponto de entrada do gateway e loop IPC via NDJSON stdin/stdout
│   ├── configs/                # Perfis JSON embutidos de OIDs NTCIP e UTMC
│   ├── evp_go/                 # Despachante de Preempção EVP em Microssegundos
│   ├── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
│   └── web_gateway/            # Gateway HTTP/SSE (Porta 2201), Malha Tailscale & Handlers CCO
├── src_tsx/                    # Aplicação Web da Central de Controle Operacional (CCO)
│   └── src_cco/                # React 18, TypeScript, Tailwind CSS, Camadas SVG, ECharts
├── src/                        # Código-fonte Principal em Python
│   ├── agents/                 # Agentes neurais: LocalAgent (PPO), GuardianAgent, StrategistAgent
│   ├── analysis/               # Avaliador de Justificativas Semafóricas MUTCD, WarrantMath e Análise
│   ├── blocks/                 # Construtor modular .docx, conversores de matemática OMML e sanitizadores
│   ├── central_controller.py   # Servidor gRPC de telemetria de alta frequência
│   ├── communication/          # MonitorClient, servidor HFT e ponte externa de telemetria
│   ├── controller/             # ConnectionManager, FailSafeManager, StageValidator e sobreposições
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, ActionAuthorizer e PopulationManager
│   ├── database/               # DatabaseEngine, DatabaseWorker e StepDecisionWorker
│   ├── drivers/                # Proxy GoGatewayClient, DriverFactory, IncidentReporter e IncidentFilter
│   ├── engine/                 # EpisodeRunner, StepProcessor, Otimizadores PPO/DQN e Treinadores
│   ├── evp/                    # Preempção de Emergência (EVPService, Cinemática, PreemptionEngine)
│   ├── fenix/                  # F.E.N.I.X. Auto-cura e Supervisão de Processos (Supervisor, Runner, Reconciler)
│   ├── handlers/               # Handlers de requisições de IA, comandos de UI e comandos de Watchdog
│   ├── launcher/               # ProcessManager, SingleInstanceLock e UITrayManager
│   ├── manager/                # CycleManager, StageTransitionManager, TopologyManager & ServiceManager
│   ├── maturity/               # MaturityManager, AgentMaturity, PromotionService, Config e Port
│   ├── mfd/                    # Analisador e Worker do Diagrama Fundamental Macroscópico (MFD)
│   ├── models/                 # Arquiteturas Neurais (PAE, TCN, ST-GATv2 Lite)
│   ├── optimizer/              # Treinamento Baseado em População (PBT) e Ajuste de Hiperparâmetros
│   ├── promotion/              # MaturityPacingCalculator, PerformanceMarginCalculator e PromotionEvaluator
│   ├── rendering/              # StaticMapRenderer e AsyncHeatmapRenderer
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo e CloudVaultRepo
│   ├── safety/                 # Processo GuardianWorker e roteamento de sinais IPC
│   ├── sas/                    # Smart Analysis System (Análise Estatística de Infraestrutura)
│   ├── sds/                    # Smart Dashboard Service (Ponte de UI Flet e WebSockets)
│   ├── security/               # Subsistema Desacoplado de Segurança (Auth, PBKDF2, Lockdown, Repositórios)
│   ├── settings/               # Configurações Modulares (Interfaces SOLID, schemas, INI e .env)
│   ├── slm/                    # Small Language Model (Inferência offline Qwen3.5 2B / llama.cpp)
│   ├── transports/             # Transportes polimórficos (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Paths e Cálculo de Episódios
│   ├── watchdog/               # Monitor de heartbeat em tempo real e fail-safe de emergência
│   └── xai/                    # Atribuição por Gradientes Integrados (Captum), gerador de laudos e worker
│
├── ui/                         # Aplicação Desktop Nativa em Flet
│   ├── cards/                  # Cards modulares de telemetria e configurações (MonitorSettingsCard)
│   ├── handlers/               # Handlers de eventos, SettingsHandler e SystemTrayHandler nativo
│   ├── views/                  # DashboardView, PlanningView, DiagnosticsView, SettingsView
│   ├── widgets/                # LiveCanvasMapWidget, PlanningControlPanel, MFDViewer, XAIViewer
│   ├── renderers/              # PlanningMapRenderer, MapVisualSyncer, MapDrawer
│   ├── animators/              # MapAnimator e controladores de transição
│   └── locales/                # Dicionários multilíngues JSON (pt_br, en_us, es_es, etc.)
│
└── tests/                      # Suíte de Testes Pytest (Unitários, Integração e Mocks de Hardware)
```

---

## 📖 Dimensões do Sistema & Navegação no Vault

### 1. Infraestrutura Central & Drivers de Hardware
- **[Arquitetura do Sistema](architecture.md)**: Blueprint técnico detalhando os 8 microsserviços concorrentes, isolamento por `multiprocessing`, canais IPC de Pipes e Filas, e ciclo de execução.
- **[Controladores Físicos & Gateway Go](hardware_drivers.md)**: Especificações do Gateway compilado em Go (`carina-go`), IPC anônimo via pipes NDJSON, NTCIP 1202 (ASC), UTMC / UTMC2 britânico, cliente SNMP v2c/v3, pool de conexões e reversão atômica de fail-safe.
- **[Referência de APIs & Protocolo HFT](api_reference.md)**: Especificação completa da interface gRPC `Synapse HFT`, telemetria externa do Monitor (MQTT/HTTP), endpoints Prometheus (porta 8001) e esquemas de filas IPC.
- **[Banco de Dados & Armazenamento Delta](database_and_schemas.md)**: Especificações do `DatabaseWorker`, `StepDecisionWorker`, pool de conexões, 12-Factor `.env` e persistência delta em PostgreSQL (97,9% de redução).
- **[Segurança & Autenticação](security_and_auth.md)**: Gestão de contas de usuários, hashing salted PBKDF2, defesa contra ataques de força bruta e controle de acesso baseado em papéis.
- **[Arquitetura Modular de Configurações](architecture.md#4-arquitetura-modular-de-configuracoes-srcsettings)**: Subsistema de configuração SOLID desacoplando esquemas, persistência em arquivo INI e segredos do `.env`.
- **[Monitoramento Polimórfico & Transportes](architecture.md#5-arquitetura-polimorfica-de-monitoramento-srctransports)**: Transmissão de telemetria e incidentes sobre corretores MQTT e endpoints em nuvem HTTP/REST/Ngrok.

### 2. Inteligência Artificial & Segurança Neuro-Simbólica
- **[Notas de Pesquisa & Formulações Neurais](research_notes.md)**: Formulações matemáticas de PPO-TCN, projeção latente $Z$ do Autoencoder Preditivo (PAE), streams de valor/vantagem do Dueling DQN-TCN, Atenção em Grafos ST-GATv2 Lite e currículo de maturação DA SILVA.
- **[Segurança, Watchdog & F.E.N.I.X.](safety_and_watchdog.md)**: Inventário de regras de Veto Simbólico (SR-00 a SR-06), limites de Veto Neural do PAE, monitoramento de heartbeat do Watchdog (< 500 ms) e auto-cura com F.E.N.I.X.
- **[IA Explicável (XAI), Auditoria Forense & SAS](xai_and_sas.md)**: Pipeline modular de XAI, atribuição de características com Google Captum Integrated Gradients e laudos periciais para auditorias municipais.
- **[Motor de Laudos Periciais & Equações](report_blocks_and_templates.md)**: Geração automatizada de relatórios periciais Word (`.docx`) em conformidade com ABNT NBR 14724 contendo fórmulas nativas em Office Math Markup Language (OMML).
- **[Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md)**: Inferência local 100% offline (Qwen3.5 2B / llama.cpp) gerando justificativas forenses textuais sem dependências de nuvem.

### 3. Física de Tráfego, Warrants & Gráficos
- **[Justificativas Semafóricas MUTCD](traffic_engineering_warrants.md)**: Avaliação automatizada de critérios regulatórios MUTCD / FHWA (Warrants 1, 2, 3 e 4) e justificativas de implantação semafórica.
- **[Diagrama Fundamental Macroscópico (MFD)](mfd_and_analytics.md)**: Relações macroscópicas de fluxo e densidade na malha urbana, densidade crítica ($K_{crit}$), perimeter gating e detecção de queda de capacidade (*capacity drop*).
- **[Renderização de Mapas & Mapas de Calor](rendering_and_heatmaps.md)**: Parser vetorial offline de redes viárias SUMO `.net.xml` e mapas de calor assíncronos baseados em Estimativa de Densidade por Kernel (KDE).

### 4. Interface Desktop & Operações
- **[Interface Desktop Flet & Visão de Planejamento](ui_and_dashboard.md)**: Arquitetura da interface nativa em Flet/Flutter, visualização de planos semafóricos, socket de instância única (porta 42123) e streaming de telemetria.
- **[Guias de Desenvolvimento & Extensão](developer_guides.md)**: Guia de configuração de ambiente de desenvolvimento, adição de novos agentes, configurações modulares e simulação de viaturas.
- **[Diretrizes de Testes & Validação](testing.md)**: Execução de testes automatizados com `pytest` (861 testes), relatórios de cobertura de código, mocks de controladores físicos e testes do Guardião.
- **[Implantação, Empacotamento & Containers](deployment_and_packaging.md)**: Guia de containerização Docker multi-stage, portas de rede, daemons do Systemd e malhas Tailscale.

### 5. Preempção de Emergência & Operações Remotas (EVP / CCO)
- **[Preempção de Veículos de Emergência & Operações Remotas](evp_and_preemption.md)**: Especificações do motor de Preempção de Veículos de Emergência (EVP), conformidade CONTRAN Res. 960 / CTB Art. 29, cinemática Haversine, gatilho de dois fatores, watchdog de dwell de 45s, despachante Go em microssegundos, malha segura Tailscale Funnel e aplicação web da Central de Controle Operacional (CCO) (`src_tsx/src_cco`).

---

> 💡 **Grafo de Conhecimento no Obsidian:** Esta documentação possui suporte nativo integral ao [Obsidian](https://obsidian.md/). Abra a pasta raiz `CARINA_CORE` como um Obsidian Vault para navegar de forma interativa por links bidirecionais e grafos visuais.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
