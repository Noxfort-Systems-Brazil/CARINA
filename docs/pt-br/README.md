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
| 🏛️ **[Arquitetura do Sistema](architecture.md)** | Especificação de Arquitetura | 8 microsserviços concorrentes de SO, dono único `CARINA_GATEWAY_ROLE`, ST-GATv2 Lite, iTransformer PAE e QR-D3QN. |
| 🚑 **[Preempção de Emergência (EVP)](evp_and_preemption.md)** | Preempção de Veículos de Socorro | Corredores verdes autônomos, cinemática Haversine ($60\text{--}160\text{ m}$), sincronia entre processos e Web Gateway protegido por token (porta 2201). |
| 🔌 **[Controladores Físicos e Gateway Go](hardware_drivers.md)** | Integração de Campo | Gateway Go com dono único (`carina-go`), IPC por pipes NDJSON, NTCIP 1202 (`.4.1.*`/`.5.1.*`), UTMC2, SNMPv3 USM, decodificação em malha fechada e traps binárias. |
| 🛡️ **[Segurança, Watchdog e F.E.N.I.X.](safety_and_watchdog.md)** | Segurança Neuro-Simbólica | `PhysicalActionMasker`, regras simbólicas (SR-00 a SR-06), calibração `CHILD` QR-D3QN + Noisy-OR, Watchdog e handover em malha fechada com F.E.N.I.X. |
| ⚡ **[API Synapse HFT e Filas IPC](api_reference.md)** | Interface de Alta Frequência | gRPC Synapse HFT (TLS/mTLS e auth Bearer, porta 50051), 12 filas IPC delimitadas + 1 pipe thread-safe e broadcast CCO com pinning. |
| 🗄️ **[Banco de Dados e Armazenamento Delta](database_and_schemas.md)** | Persistência Relacional | Armazenamento delta no PostgreSQL (**redução de 97,9%**), `PostgresConnectionPool`, SQLite WAL, SQL `make_interval` e retenção EVP de 168h. |
| 🧠 **[Notas de Pesquisa e Formulações](research_notes.md)** | Formulações Matemáticas | TCN unificada (`GroupNorm` + `SiLU`), batching via `torch.vmap`, iTransformer PAE, QR-D3QN + Noisy-OR, ST-GATv2 CTDE e DA SILVA binário ($\ln 2$). |
| 🚦 **[Critérios Semafóricos MUTCD](traffic_engineering_warrants.md)** | Engenharia de Tráfego | Avaliação algorítmica de justificativas regulatórias FHWA/MUTCD (Warrants 1, 2, 3 e 4) a partir de históricos reais. |
| 📈 **[Diagrama Fundamental Macroscópico (MFD)](mfd_and_analytics.md)** | Física de Tráfego de Redes | Regressões de fluxo-densidade, detecção de queda de capacidade (*capacity drop*), perimeter gating e cache de filtros de incidentes. |
| 🔍 **[IA Explicável (XAI) e Laudo ABNT](xai_and_sas.md)** | Auditoria Forense Municipal | Google Captum Integrated Gradients (pipeline multiagente com cache), as 5 equações formais e auditoria dos vetos do Guardião. |
| 📄 **[Motor de Laudos Word ABNT](report_blocks_and_templates.md)** | Documentação Automatizada | Geração de laudos `.docx` conforme ABNT NBR 14724 com equações nativas em OMML e `ReportNumberFormatter` com cache via `stat`. |
| 🤖 **[Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md)** | IA Local e Privativa | Qwen3.5 2B / llama.cpp local serializado por `slm_process_lock`, sondagem de VRAM via `pynvml` e `unload()` explícito. |
| 🖥️ **[Interface Desktop Flet e Planejamento](ui_and_dashboard.md)** | Arquitetura Frontend | Interface desktop Flet, CCO React 18 (animações no compositor e viewport rAF), pausa de `MapAnimator` em janela oculta e `AuditLogWidget` paginado. |
| 🗺️ **[Renderização de Mapas e Heatmaps](rendering_and_heatmaps.md)** | Visualização Geoespacial | Cache LRU do `.net.xml` SUMO (`read_sumo_net_cached`), renderização offscreen em `mpl_utils` e mapas de calor KDE assíncronos. |
| 🔐 **[Segurança e Autenticação](security_and_auth.md)** | Governança e Acesso | RBAC, lockdown com PBKDF2 salted, gRPC TLS/mTLS e auth Bearer, Web Gateway fail-closed `503` e certificate pinning SHA-256. |
| 🛠️ **[Guias de Desenvolvimento](developer_guides.md)** | Engenharia e Extensão | Configurações 12-Factor `.env` e `[SYNAPSE]`, `CARINA_GATEWAY_ROLE`, protocolos segregados em `src/interfaces/` e agentes customizados. |
| 🧪 **[Diretrizes de Testes e Validação](testing.md)** | Garantia de Qualidade | **967 testes Pytest** (935 unitários, 18 de integração, 14 raiz), **46 testes unitários em Go**, `scripts/pytest_limited.sh` e `tests/memory_guard.py`. |
| 🚀 **[Implantação e Empacotamento](deployment_and_packaging.md)** | Operações e Produção | Builds Docker multi-stage, daemons Systemd, Web Gateway fail-closed zero-trust e implantação com Tailscale Funnel. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
