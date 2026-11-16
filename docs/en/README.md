<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — Technical Documentation Suite
### System Architecture, Hardware Integration & Safety Framework
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Translations:** **[🇺🇸 English](README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Central Hub](../index.md)**

---

</div>

## Welcome to the Official Technical Documentation

This directory contains the canonical English documentation suite for **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — an enterprise deep reinforcement learning ecosystem designed for distributed urban traffic light control.

## Technical Guide Directory

| Document | Topic | Key Contents |
|---|---|---|
| 📚 **[Central Master (MOC)](carina_moc.md)** | Master Index & Knowledge Graph | Codebase overview, architectural directory hierarchy, and Obsidian bi-directional graph. |
| 📖 **[System Architecture](architecture.md)** | Core Architecture | 8 concurrent OS microservices, `CARINA_GATEWAY_ROLE` single owner, ST-GATv2 Lite, iTransformer PAE, and QR-D3QN. |
| 🚑 **[Emergency Preemption (EVP)](evp_and_preemption.md)** | Emergency Vehicle Preemption | Autonomous green corridors, Haversine kinematics ($60\text{--}160\text{ m}$), cross-process sync, and token-protected Web Gateway (port 2201). |
| 🔌 **[Hardware Drivers & Go Gateway](hardware_drivers.md)** | Field Controllers | Single-owner Go Gateway (`carina-go`), NDJSON pipe IPC, NTCIP 1202 (`.4.1.*`/`.5.1.*`), UTMC2, SNMPv3 USM, closed-loop stage decoding, and binary traps. |
| 🛡️ **[Safety Architecture, Watchdog & FENIX](safety_and_watchdog.md)** | Neuro-Symbolic Safety | `PhysicalActionMasker`, symbolic rules (SR-00 to SR-06), QR-D3QN + Noisy-OR `CHILD` calibration, Watchdog, and F.E.N.I.X. closed-loop handover. |
| ⚡ **[Synapse HFT API & IPC Queues](api_reference.md)** | High-Frequency Interface | Synapse HFT gRPC (TLS/mTLS & Bearer auth, port 50051), 12 bounded IPC queues + 1 thread-safe pipe, and pinned CCO broadcasting. |
| 🗄️ **[Database Architecture & Schemas](database_and_schemas.md)** | Persistence & Schemas | PostgreSQL delta storage (**97.9% reduction**), `PostgresConnectionPool`, SQLite WAL, `make_interval` SQL, and 168h EVP retention. |
| 🧠 **[Neural Research & Formulations](research_notes.md)** | Mathematical Modeling | Unified TCN (`GroupNorm` + `SiLU`), `torch.vmap` batching, iTransformer PAE, QR-D3QN + Noisy-OR, ST-GATv2 CTDE, and binary DA SILVA ($\ln 2$). |
| 🚦 **[Traffic Signal Warrants (MUTCD)](traffic_engineering_warrants.md)** | Traffic Engineering | Algorithmic evaluation of formal FHWA/MUTCD regulatory signal warrants (Warrants 1, 2, 3, 4). |
| 📈 **[MFD & Network Traffic Analytics](mfd_and_analytics.md)** | Macroscopic Physics | Macroscopic Fundamental Diagram (MFD) regressions, capacity drop mitigation, perimeter gating, and incident filter cache. |
| 🔍 **[Explainable AI (XAI) & SAS](xai_and_sas.md)** | Municipal Audit & XAI | Google Captum Integrated Gradients (cached multi-agent pipeline), 5 formal equations, and Guardian veto forensic audit engine. |
| 📄 **[Report Blocks Engine](report_blocks_and_templates.md)** | Automated Reporting | ABNT NBR 14724 Word (.docx) generation with OMML equations and stat-cached `ReportNumberFormatter`. |
| 🤖 **[Small Language Models (SLM)](slm_and_local_llm.md)** | Offline Private AI | Local Qwen3.5 2B / llama.cpp serialized via `slm_process_lock`, `pynvml` VRAM probing, and explicit `unload()`. |
| 🖥️ **[Desktop UI & Planning View](ui_and_dashboard.md)** | Frontend Architecture | Flet desktop GUI, React 18 CCO (compositor animations & rAF viewport), `MapAnimator` window pause, and paginated `AuditLogWidget`. |
| 🗺️ **[Vector Map Rendering & Heatmaps](rendering_and_heatmaps.md)** | Geospatial Visualization | SUMO `.net.xml` LRU cache (`read_sumo_net_cached`), offscreen `mpl_utils` rendering, and asynchronous KDE heatmaps. |
| 🔐 **[Security & Authentication](security_and_auth.md)** | Governance & Access | RBAC, salted PBKDF2 lockdown, gRPC TLS/mTLS & Bearer auth, fail-closed `503` Web Gateway, and SHA-256 certificate pinning. |
| 🛠️ **[Developer Guides](developer_guides.md)** | Engineering & Extension | 12-Factor `.env` & `[SYNAPSE]` settings, `CARINA_GATEWAY_ROLE`, segregated `src/interfaces/` protocols, and custom agents. |
| 🧪 **[Testing & Quality Assurance](testing.md)** | QA & Test Suite | **967 Pytest tests** (935 unit, 18 integration, 14 root), **46 Go unit tests**, `scripts/pytest_limited.sh`, and `tests/memory_guard.py`. |
| 🚀 **[Deployment & Packaging](deployment_and_packaging.md)** | Operations & Packaging | Multi-stage Docker builds, Systemd daemons, zero-trust fail-closed Web Gateway, and Tailscale Funnel deployment. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
