<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — Suíte de Documentação Técnica
### Arquitetura de Sistemas, Integração de Hardware e Segurança Semafórica
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Ativo-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Idiomas:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português (Brasil)](README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Central de Documentação](../index.md)**

---

</div>

## Bem-vindo à Documentação Técnica Oficial

Este diretório reúne toda a suíte canônica de documentação técnica em **Português do Brasil** do ecossistema **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — ecossistema corporativo de Aprendizado por Reforço Profundo distribuído para controle semafórico adaptativo urbano em tempo real.

## Índice Completo de Guias Especializados

| Documento | Tema & Escopo | Principais Tópicos |
|---|---|---|
| 📚 **[Central Master (MOC)](carina_moc.md)** | Índice e Grafo de Conhecimento | Visão geral da base de código, mapa hierárquico e navegação bidirecional no Obsidian. |
| 🏛️ **[Arquitetura do Sistema](architecture.md)** | Especificação de Arquitetura | 8 microsserviços concorrentes de SO, atenção em grafos ST-GATv2 Lite, Autoencoder Preditivo PAE, PBT Intra-Fase, balanceamento físico de recompensas e aceleração universal com AMP/TensorCores. |
| 🚑 **[Preempção de Emergência (EVP)](evp_and_preemption.md)** | Preempção de Veículos de Socorro | Corredores verdes autônomos, portais cinemáticos Haversine ($60\text{--}160\text{ m}$), Gateway Web em Go (porta 2201) e videowall CCO em React. |
| 🔌 **[Controladores Físicos e Gateway Go](hardware_drivers.md)** | Integração de Campo | Gateway industrial de hardware compilado em Go (`bin/carina-go`), IPC anônimo via pipes NDJSON de porta zero, NTCIP 1202, UTMC2 e fail-safe atômico. |
| 🛡️ **[Segurança, Watchdog e F.E.N.I.X.](safety_and_watchdog.md)** | Segurança Neuro-Simbólica | Regras de veto físico inviolável (SR-01 a SR-05), D3QN Guardian contra spillback, Watchdog de tempo real (< 500 ms) e ressurreição autônoma com F.E.N.I.X. |
| ⚡ **[API Synapse HFT e Filas IPC](api_reference.md)** | Interface de Alta Frequência | Interface gRPC de sub-milissegundo Synapse HFT (porta 50051), 11 canais de filas IPC e transporte polimórfico de telemetria (MQTT e HTTP/REST). |
| 🗄️ **[Banco de Dados e Armazenamento Delta](database_and_schemas.md)** | Persistência Relacional | Motor assíncrono de persistência com compressão delta em PostgreSQL (**redução de 97,9% no consumo em disco**), enums Smallint de 1 byte e 12-Factor `.env`. |
| 🧠 **[Notas de Pesquisa e Formulações](research_notes.md)** | Formulações Matemáticas | Modelagem matemática PPO-TCN, Autoencoder Preditivo PAE, Dueling DQN, ST-GATv2 Lite e currículo de maturação DA SILVA. |
| 🚦 **[Critérios Semafóricos MUTCD](traffic_engineering_warrants.md)** | Engenharia de Tráfego | Avaliação algorítmica de justificativas regulatórias FHWA/MUTCD (Warrants 1, 2, 3 e 4) a partir de históricos reais. |
| 📈 **[Diagrama Fundamental Macroscópico (MFD)](mfd_and_analytics.md)** | Física de Tráfego de Redes | Regressões de fluxo-densidade, detecção de queda de capacidade (*capacity drop*), perimeter gating e cache de filtros de incidentes. |
| 🔍 **[IA Explicável (XAI) e Laudo ABNT](xai_and_sas.md)** | Auditoria Forense Municipal | Google Captum Integrated Gradients, as 5 equações matemáticas formais e auditoria dos vetos do Guardião. |
| 📄 **[Motor de Laudos Word ABNT](report_blocks_and_templates.md)** | Documentação Automatizada | Geração de laudos periciais `.docx` em conformidade estrita com ABNT NBR 14724 com equações nativas em OMML. |
| 🤖 **[Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md)** | IA Local e Privativa | Justificativas textuais periciais geradas 100% offline via Qwen3.5 2B / llama.cpp sem vazamento para provedores em nuvem. |
| 🖥️ **[Interface Desktop Flet e Planejamento](ui_and_dashboard.md)** | Arquitetura Frontend | Interface desktop nativa em Flet/Flutter, visão vetorial de planejamento semafórico, bandeja do sistema (Tray) e bloqueio de instância única (porta 42123). |
| 🗺️ **[Renderização de Mapas e Heatmaps](rendering_and_heatmaps.md)** | Visualização Geoespacial | Parser vetorial SUMO `.net.xml` e mapas de calor contínuos assíncronos baseados em Kernel Density Estimation (KDE). |
| 🔐 **[Segurança e Autenticação](security_and_auth.md)** | Governança e Acesso | Controle de acesso baseado em papéis (RBAC), hashing salted PBKDF2, proteção contra força bruta e isolamento 12-Factor. |
| 🛠️ **[Guias de Desenvolvimento](developer_guides.md)** | Engenharia e Extensão | Setup de ambiente, implementação de novos agentes neurais, simulação de viaturas e arquitetura de configurações modulares SOLID. |
| 🧪 **[Diretrizes de Testes e Validação](testing.md)** | Garantia de Qualidade | Suíte Pytest com **861 testes automatizados**, testes Go nativos (`go test`), mocks determinísticos do Guardian e verificação de cobertura de código. |
| 🚀 **[Implantação e Empacotamento](deployment_and_packaging.md)** | Operações e Produção | Containerização Docker multi-stage com aceleração CUDA, tabela de portas de rede e daemons de inicialização Systemd no Linux. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
