---
tags: [moc, hub, docs, obsidian, carina, indice]
aliases: [CARINA MOC, Central Master de Documentação, Índice de Documentação, Vault de Conhecimento]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA: Central Master de Documentação Técnica (MOC)
### Índice Geral e Grafo de Conhecimento Multiagente
*Noxfort Systems — A State Of Art Company*

</div>

Bem-vindo à biblioteca técnica do **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture). Projetado como um ecossistema de Aprendizado por Reforço Profundo de alta frequência e massivamente concorrente para controle semafórico adaptativo em tempo real, o CARINA une IA neuro-simbólica, atuação física de campo de baixa latência e isolamento rigoroso de múltiplos processos no sistema operacional.

Este índice mestre de documentação fornece cobertura técnica profunda para desenvolvedores de núcleo, pesquisadores acadêmicos, engenheiros de tráfego municipais e integradores de sistemas. É 100% compatível tanto com o **GitHub** quanto com o **[Obsidian](https://obsidian.md/)**.

⬅️ [Central em Português](README.md) | 🏛️ [Arquitetura do Sistema](architecture.md) | ⚡ [Referência de APIs](api_reference.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 🗺️ Mapa da Base de Código e Hierarquia de Diretórios

```text
CARINA_CORE/
├── carina.py                   # Orquestrador Mestre (SingleInstanceLock, ProcessManager, UI/Bandeja)
├── ARCHITECTURE.md             # Blueprint de Arquitetura com 8 Processos e Topologia IPC
├── pyproject.toml              # Toolchain de build e metadados do projeto
├── requirements.txt            # Dependências de execução em Python
├── .env.example                # Variáveis de ambiente e credenciais (Padrão 12-Factor)
│
├── config/                     # Sistemas de Configuração
│   ├── settings.ini            # Parâmetros globais (IA, PBT, Watchdog, MFD, Logging)
│   ├── database/               # Esquemas e queries SQL dinâmicas (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Regras de segurança e consistência semântica (safety_rules.json, semantic_rules.json)
│   └── templates/              # Templates multilíngues de laudos, MFD, SAS e XAI
│
├── proto/                      # Especificações do Protocolo gRPC
│   └── synapse_hft.proto       # Definições Protobuf para telemetria de alta frequência e atuação
│
├── docs/                       # Vault Geral de Documentação Técnica
│   ├── pt-br/                  # Suíte Completa em Português do Brasil
│   └── ...
│
├── bin/                        # Binários nativos compilados (carina-go)
├── src_go/                     # Gateway de Hardware em Go (NTCIP 1202, UTMC2, UDP 161/162)
│   ├── cmd/gateway/            # Entrypoint do gateway e loop IPC via NDJSON stdin/stdout
│   ├── configs/                # Perfis JSON embutidos de OIDs NTCIP e UTMC
│   └── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
│
├── src/                        # Código-fonte Principal em Python
│   ├── agents/                 # Agentes neurais: LocalAgent (PPO), GuardianAgent, ConsultantAgent, StrategistAgent
│   ├── analysis/               # Avaliador de Justificativas Semafóricas MUTCD, WarrantMath e análise
│   ├── blocks/                 # Construtor modular .docx, conversores de matemática OMML e sanitizadores
│   ├── central_controller.py   # Servidor gRPC de telemetria de alta frequência
│   ├── communication/          # MonitorClient, servidor HFT e ponte externa de telemetria
│   ├── controller/             # ConnectionManager, FailSafeManager, StageValidator e sobreposições
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, MaturityManager e ActionAuthorizer
│   ├── database/               # DatabaseEngine, DatabaseWorker e StepDecisionWorker
│   ├── drivers/                # Proxy GoGatewayClient, DriverFactory, IncidentReporter e IncidentFilter
│   ├── engine/                 # EpisodeRunner, StepProcessor, Otimizadores PPO/DQN e Treinadores
│   ├── fenix/                  # F.E.N.I.X. Auto-cura e Supervisão de Processos (Supervisor, Runner, Reconciler)
│   ├── handlers/               # Handlers de requisições de IA, comandos de UI e comandos de Watchdog
│   ├── launcher/               # ProcessManager, SingleInstanceLock e UITrayManager
│   ├── mfd/                    # Analisador e Worker do Diagrama Fundamental Macroscópico (MFD)
│   ├── models/                 # Arquiteturas Neurais (PAE, TCN, ST-GATv2 Lite, CrossAttention)
│   ├── rendering/              # StaticMapRenderer e AsyncHeatmapRenderer
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo e CloudVaultRepo
│   ├── safety/                 # Processo GuardianWorker e roteamento de sinais IPC
│   ├── sas/                    # Smart Analysis System (Análise Estatística de Infraestrutura)
│   ├── sds/                    # Smart Dashboard Service (Ponte de UI Flet e WebSockets)
│   ├── settings/               # Configurações Modulares (Interfaces SOLID, schemas, INI e .env)
│   ├── slm/                    # Small Language Model (Inferência offline Qwen3 / llama.cpp)
│   ├── transports/             # Transportes polimórficos (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Paths e Subsistema de Segurança
│   │   └── security/           # AuthService, UserService, Hasher Bcrypt e LockdownManager
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

## 📖 Dimensões do Sistema e Navegação no Vault

### 1. Infraestrutura Central e Drivers de Hardware
- **[Arquitetura do Sistema](architecture.md)**: Blueprint técnico detalhando os 8 microsserviços concorrentes, isolamento por `multiprocessing`, canais IPC de Pipes e Filas, e ciclo de execução.
- **[Controladores Físicos e Gateway Go](hardware_drivers.md)**: Especificações do Gateway compilado em Go (`carina-go`), IPC anônimo via pipes NDJSON, NTCIP 1202 (ASC), UTMC / UTMC2 britânico, cliente SNMP v2c/v3, pool de conexões e reversão atômica de fail-safe.
- **[Referência de APIs e Protocolo HFT](api_reference.md)**: Especificação completa da interface gRPC `Synapse HFT`, telemetria externa do Monitor (MQTT/HTTP), endpoints Prometheus (porta 8001) e esquemas de filas IPC.
- **[Banco de Dados e Armazenamento Delta](database_and_schemas.md)**: Especificações do `DatabaseWorker`, `StepDecisionWorker`, pool de conexões, 12-Factor `.env` e persistência delta em PostgreSQL (97,9% de redução).
- **[Segurança e Autenticação](security_and_auth.md)**: Gestão de contas de usuários, hashing salted `bcrypt`, defesa contra ataques de força bruta e controle de acesso baseado em papéis.

### 2. Inteligência Artificial e Segurança Neuro-Simbólica
- **[Notas de Pesquisa e Formulações Neurais](research_notes.md)**: Formulações matemáticas de PPO-TCN, projeção latente $Z$ do Autoencoder Preditivo (PAE), streams de valor/vantagem do Dueling DQN-TCN, Atenção em Grafos ST-GATv2 Lite e currículo de maturação DA SILVA.
- **[Segurança, Watchdog e F.E.N.I.X.](safety_and_watchdog.md)**: Inventário de regras de Veto Simbólico (SR-01 a SR-05), limites de Veto Neural do PAE, monitoramento de heartbeat do Watchdog (< 500 ms) e auto-cura com F.E.N.I.X.
- **[IA Explicável (XAI) e Laudo ABNT](xai_and_sas.md)**: Pipeline modular de XAI, atribuição de características com Google Captum Integrated Gradients e laudos periciais para auditorias municipais.
- **[Motor de Laudos Periciais e Equações](report_blocks_and_templates.md)**: Geração automatizada de relatórios periciais Word (`.docx`) em conformidade com ABNT NBR 14724 contendo fórmulas nativas em Office Math Markup Language (OMML).
- **[Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md)**: Inferência local 100% offline (Qwen3 1.7B / llama.cpp) gerando justificativas forenses textuais sem dependências de nuvem.

### 3. Física de Tráfego, Warrants e Gráficos
- **[Justificativas Semafóricas MUTCD](traffic_engineering_warrants.md)**: Avaliação automatizada de critérios regulatórios MUTCD / FHWA (Warrants 1, 2, 3, 7 e 8) e justificativas de implantação semafórica.
- **[Diagrama Fundamental Macroscópico (MFD)](mfd_and_analytics.md)**: Relações macroscópicas de fluxo e densidade na malha urbana, densidade crítica ($K_{crit}$), perimeter gating e detecção de queda de capacidade (*capacity drop*).
- **[Renderização de Mapas e Mapas de Calor](rendering_and_heatmaps.md)**: Parser vetorial offline de redes viárias SUMO `.net.xml` e mapas de calor assíncronos baseados em Estimativa de Densidade por Kernel (KDE).

### 4. Interface Desktop e Operações
- **[Interface Desktop Flet e Planejamento](ui_and_dashboard.md)**: Arquitetura da interface nativa em Flet/Flutter, visualização de planos semafóricos, socket de instância única (porta 42123) e streaming de telemetria.
- **[Guias de Desenvolvimento e Extensão](developer_guides.md)**: Guia de configuração de ambiente de desenvolvimento, adição de novos agentes, configurações modulares e empacotamento.
- **[Diretrizes de Testes e Validação](testing.md)**: Execução de testes automatizados com `pytest`, relatórios de cobertura de código, mocks de controladores físicos e testes do Guardião.
- **[Implantação, Empacotamento e Containers](deployment_and_packaging.md)**: Guia de containerização Docker multi-stage, daemons do Systemd e pacotes Debian `.deb`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3.</small>
</div>
