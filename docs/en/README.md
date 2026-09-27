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

🌐 **Translations:** **[🇺🇸 English](README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Central Hub](../README.md)**

---

</div>

## Welcome to the Official Technical Documentation

This directory contains the canonical English documentation suite for **CARINA** (Cognitive Autonomous Real-time Intersection Network Architecture) — an enterprise deep reinforcement learning ecosystem designed for distributed urban traffic light control.

## Technical Guide Directory

| Document | Topic | Key Contents |
|---|---|---|
| 📖 **[System Architecture](architecture.md)** | Core Architecture | 8 concurrent OS microservices, ST-GATv2 Lite Graph Attention, Consultant PAE (128-channel), and Universal AMP acceleration. |
| 🔌 **[Hardware Drivers & Go Gateway](hardware_drivers.md)** | Field Controllers | Industrial Go Hardware Gateway (`carina-go`), zero-port NDJSON pipe IPC, NTCIP 1202, UTMC2, SNMP client pool, and atomic fail-safe. |
| 🛡️ **[Safety Architecture, Watchdog & FENIX](safety_and_watchdog.md)** | Neuro-Symbolic Safety | Symbolic veto rules (SR-01 to SR-05), D3QN Guardian spillback vetoes, real-time Watchdog (< 500 ms), and F.E.N.I.X. auto-resurrection. |
| ⚡ **[Synapse HFT API & IPC Queues](api_reference.md)** | High-Frequency Interface | Sub-millisecond Synapse HFT gRPC interface (port 50051), 10 bounded IPC channels, and polymorphic telemetry transports. |
| 🗄️ **[Database Architecture & Schemas](database_and_schemas.md)** | Persistence & Schemas | PostgreSQL asynchronous delta storage engine achieving **97.9% storage reduction**, 1-byte Smallint enums, and 12-Factor `.env`. |
| 🧪 **[Testing & Quality Assurance](testing.md)** | QA & Test Suite | Pytest suite covering 53 unit test modules, native Go unit tests (`go test`), Guardian safety mocks, and coverage validation. |
| 🔍 **[Explainable AI (XAI) & SAS](xai_and_sas.md)** | Municipal Audit & XAI | Google Captum Integrated Gradients, 5 formal mathematical equations, and ABNT NBR 14724 forensic Word report generator. |
| 📈 **[MFD & Network Traffic Analytics](mfd_and_analytics.md)** | Macroscopic Physics | Macroscopic Fundamental Diagram (MFD) regressions, capacity drop mitigation, perimeter gating, and incident filter cache. |
| 🖥️ **[Desktop UI & Planning View](ui_and_dashboard.md)** | Frontend Architecture | Native Flet desktop GUI, interactive vector planning view, system tray management, and single instance lock (port 42123). |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i>
</div>
