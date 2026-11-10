---
tags: [home, index, carina, hub]
aliases: [Documentation Index, Overview, Portal]
---

<div align="center">

<img src="assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA Documentation Hub
### Technical Master Portal & Architecture Index
*Noxfort Systems — A State Of Art Company*

</div>

Welcome to the technical documentation library for **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — an enterprise deep reinforcement learning ecosystem for urban traffic light networks.

Designed to operate seamlessly on **GitHub** and as an **[Obsidian](https://obsidian.md/) Knowledge Vault**, this documentation suite covers all 8 concurrent OS processes, neuro-symbolic safety firewalls, physical hardware drivers, and forensic municipal audit pipelines.

---

## 🗺️ Master Navigation & Modules

| Subsystem / Dimension | Focus Area | Direct Link |
| :--- | :--- | :---: |
| 📚 **Master Map of Content** | Primary Obsidian Hub & Codebase Directory Map | [Explore Hub](CARINA_MOC.md) |
| 🏛️ **System Architecture** | 8 Concurrent OS Processes, ST-GATv2 Lite, Universal PAE, Intra-Phase PBT & Reward Balancing | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC Telemetry & Protobuf IPC Specifications | [View API Reference](API_REFERENCE.md) |
| 🧠 **Neural Formulations** | PPO-TCN, Dilated Convolutions, ST-GATv2 Lite & DA SILVA | [View Research](RESEARCH_NOTES.md) |
| 🚦 **Hardware Drivers** | Physical Intersection Control (NTCIP 1202, UTMC2, SNMP) | [View Drivers](HARDWARE_DRIVERS.md) |
| 🛡️ **Safety Firewall & Watchdog** | Symbolic Veto Rules, D3QN Risk Overrides & Heartbeat Fail-Safe | [View Safety Guide](SAFETY_AND_WATCHDOG.md) |
| 🚑 **Emergency Preemption (EVP)** | Autonomous Green Corridors, Kinematics Gates & Web Gateway | [View EVP Guide](EVP_AND_PREEMPTION.md) |
| 📊 **Engineering Warrants** | MUTCD / FHWA Signal Justification Warrants 1, 2, 3, 4 | [View Warrants](TRAFFIC_ENGINEERING_WARRANTS.md) |
| 📈 **MFD & Traffic Analytics** | Flow-Density Curves, Capacity Drop & Perimeter Gating | [View MFD Guide](MFD_AND_ANALYTICS.md) |
| 🗄️ **Database & Schemas** | PostgreSQL Delta Storage, Smallint Enums & 12-Factor Setup | [View DB Specs](DATABASE_AND_SCHEMAS.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients, 5 Formal Equations & Audits | [View XAI & SAS](XAI_AND_SAS.md) |
| 📄 **Report Blocks Engine** | ABNT NBR 14724 Word (.docx) Builder & OMML Math Equations | [View Reports](REPORT_BLOCKS_AND_TEMPLATES.md) |
| 🤖 **Small Language Models** | Local Qwen3.5 2B / llama.cpp Offline Textual Justification | [View SLM Guide](SLM_AND_LOCAL_LLM.md) |
| 🖥️ **Desktop UI & Planning** | Native Flet GUI, Planning Canvas, System Tray & SDS | [View UI Guide](UI_AND_DASHBOARD.md) |
| 🗺️ **Rendering & Heatmaps** | Vector Map Rendering & Asynchronous Real-Time Heatmaps | [View Rendering](RENDERING_AND_HEATMAPS.md) |
| 🔐 **Security & Authentication** | User Accounts, Salted PBKDF2 Hashing & Brute-Force Lockdown | [View Security](SECURITY_AND_AUTH.md) |
| 🛠️ **Developer Guides** | Agent Development, Settings Configuration & Setup | [View Guides](DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest Suite (861 Tests), Driver Mocks & Coverage Reporting | [View Testing](TESTING.md) |
| 🚀 **Deployment & Packaging** | Docker Multi-Stage & Systemd Service Daemons | [View Deployment](DEPLOYMENT_AND_PACKAGING.md) |

---

## ⚡ Quick Architecture Summary

```text
       ┌────────────────────────────────────────────────────────┐
       │             CARINA Multiprocessing Engine              │
       │           (8 Concurrent Operating System Processes)     │
       └──────────────────────────┬─────────────────────────────┘
                                  │
      ┌───────────────────────────┼───────────────────────────┐
      ▼                           ▼                           ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────────┐
│CentralCtrl   │          │  AI Process  │          │  Hardware Drivers│
│(gRPC / HFT)  │ ◄──────► │ (PPO + GAT)  │ ◄──────► │ (NTCIP / UTMC)   │
└──────┬───────┘          └──────┬───────┘          └──────────────────┘
       │                         │
       ▼                         ▼
┌──────────────┐          ┌──────────────┐
│ Watchdog     │          │  Guardian    │
│(500ms Fallbk)│          │ (D3QN Veto)  │
└──────────────┘          └──────────────┘
```

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
