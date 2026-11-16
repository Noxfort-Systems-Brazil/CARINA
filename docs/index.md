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
| 🏛️ **System Architecture** | 8 Concurrent OS Processes, `CARINA_GATEWAY_ROLE` Single Owner, ST-GATv2 Lite, iTransformer PAE & QR-D3QN | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC Telemetry (TLS/mTLS & Bearer Auth) & 12 IPC Channels | [View API Reference](API_REFERENCE.md) |
| 🧠 **Neural Formulations** | Unified TCN, iTransformer PAE, QR-D3QN + Noisy-OR & DA SILVA | [View Research](RESEARCH_NOTES.md) |
| 🚦 **Hardware Drivers** | NTCIP 1202, UTMC2, SNMPv3 USM, Closed-Loop Decoding & Binary Traps | [View Drivers](HARDWARE_DRIVERS.md) |
| 🛡️ **Safety Firewall & Watchdog** | Symbolic Veto Rules, QR-D3QN `CHILD` Calibration, `PhysicalActionMasker` & F.E.N.I.X. | [View Safety Guide](SAFETY_AND_WATCHDOG.md) |
| 🚑 **Emergency Preemption (EVP)** | Autonomous Green Corridors, Kinematics Gates, Token Auth & Web Gateway | [View EVP Guide](EVP_AND_PREEMPTION.md) |
| 📊 **Engineering Warrants** | MUTCD / FHWA Signal Justification Warrants 1, 2, 3, 4 | [View Warrants](TRAFFIC_ENGINEERING_WARRANTS.md) |
| 📈 **MFD & Traffic Analytics** | Flow-Density Curves, Capacity Drop & Perimeter Gating | [View MFD Guide](MFD_AND_ANALYTICS.md) |
| 🗄️ **Database & Schemas** | PostgreSQL Delta Storage, `PostgresConnectionPool`, SQLite WAL & 168h EVP Purge | [View DB Specs](DATABASE_AND_SCHEMAS.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients (Cached Multi-Agent), 5 Formal Equations & Audits | [View XAI & SAS](XAI_AND_SAS.md) |
| 📄 **Report Blocks Engine** | ABNT NBR 14724 Word (.docx) Builder, OMML Math & Cached Formatters | [View Reports](REPORT_BLOCKS_AND_TEMPLATES.md) |
| 🤖 **Small Language Models** | Local Qwen3.5 2B / llama.cpp Serialized via `slm_process_lock` & `pynvml` | [View SLM Guide](SLM_AND_LOCAL_LLM.md) |
| 🖥️ **Desktop UI & Planning** | Native Flet GUI, React 18 CCO Videowall, `RemoteGatewaySettingsPersister` & SDS | [View UI Guide](UI_AND_DASHBOARD.md) |
| 🗺️ **Rendering & Heatmaps** | Vector Map Rendering, Offscreen `mpl_utils` & SUMO LRU Cache | [View Rendering](RENDERING_AND_HEATMAPS.md) |
| 🔐 **Security & Authentication** | User Accounts, PBKDF2 Lockdown, gRPC TLS/mTLS, Gateway Tokens & Cert Pinning | [View Security](SECURITY_AND_AUTH.md) |
| 🛠️ **Developer Guides** | Agent Development, Settings Configuration, `.env` Secrets & `CARINA_GATEWAY_ROLE` | [View Guides](DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest Suite (967 Tests), 46 Go Tests, `pytest_limited.sh` RAM Guard & Mocks | [View Testing](TESTING.md) |
| 🚀 **Deployment & Packaging** | Docker Multi-Stage, Systemd Daemons & Zero-Trust Fail-Closed Gateway | [View Deployment](DEPLOYMENT_AND_PACKAGING.md) |

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
