<div align="center">

<img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="110" />

# CARINA — Suíte de Documentação Técnica
### Arquitetura de Sistemas, Integração de Hardware e Segurança Semafórica
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Ativo-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Idiomas:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português (Brasil)](README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Central de Documentação](../README.md)**

---

</div>

## Bem-vindo à Documentação Técnica Oficial

Este diretório reúne toda a suíte de documentação técnica em **Português do Brasil** do ecossistema **CARINA** (Cognitive Autonomous Real-time Intersection Network Architecture) — ecossistema corporativo de Aprendizado por Reforço Profundo distribuído para controle semafórico adaptativo urbano em tempo real.

## Índice de Guias Especializados

| Documento | Tema & Escopo | Principais Tópicos |
|---|---|---|
| 📖 **[Arquitetura do Sistema](architecture.md)** | Especificação de Arquitetura | 8 microsserviços concorrentes de SO, atenção em grafos ST-GATv2 Lite, Agente Consultor PAE (128 canais) e aceleração universal com AMP/TensorCores. |
| 🔌 **[Controladores Físicos e Gateway Go](hardware_drivers.md)** | Integração de Campo | Gateway industrial de hardware compilado em Go (`bin/carina-go`), IPC anônimo via pipes NDJSON de porta zero, NTCIP 1202, UTMC2 e fail-safe atômico. |
| 🛡️ **[Segurança, Watchdog e F.E.N.I.X.](safety_and_watchdog.md)** | Segurança Neuro-Simbólica | Regras de veto físico inviolável (SR-01 a SR-05), D3QN Guardian contra spillback, Watchdog de tempo real (< 500 ms) e ressurreição autônoma com F.E.N.I.X. |
| ⚡ **[API Synapse HFT e Filas IPC](api_reference.md)** | Interface de Alta Frequência | Interface gRPC de sub-milissegundo Synapse HFT (porta 50051), 10 canais de filas IPC e transporte polimórfico de telemetria (MQTT e HTTP/REST). |
| 🗄️ **[Banco de Dados e Armazenamento Delta](database_and_schemas.md)** | Persistência Relacional | Motor assíncrono de persistência com compressão delta em PostgreSQL (**redução de 97,9% no consumo em disco**), enums Smallint de 1 byte e 12-Factor `.env`. |
| 🧪 **[Diretrizes de Testes e Validação](testing.md)** | Garantia de Qualidade | Suíte Pytest cobrindo 99 módulos (401 testes), testes Go nativos (`go test`), mocks determinísticos do Guardian e verificação de cobertura de código. |
| 🔍 **[IA Explicável (XAI) e Laudo ABNT](xai_and_sas.md)** | Auditoria Forense Municipal | Google Captum Integrated Gradients, as 5 equações matemáticas formais e gerador automático de relatórios periciais Word (.docx) compatíveis com ABNT NBR 14724. |
| 📈 **[Diagrama Fundamental Macroscópico (MFD)](mfd_and_analytics.md)** | Física de Tráfego de Redes | Regressões de fluxo-densidade, detecção de queda de capacidade (*capacity drop*), perimeter gating e cache de filtros de incidentes. |
| 🖥️ **[Interface Desktop Flet e Planejamento](ui_and_dashboard.md)** | Arquitetura Frontend | Interface desktop nativa em Flet/Flutter, visão vetorial de planejamento semafórico, bandeja do sistema (Tray) e bloqueio de instância única (porta 42123). |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i>
</div>
