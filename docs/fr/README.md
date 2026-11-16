<div align="center">

<img src="../assets/carina-logo.png" alt="Logo CARINA CORE" width="120" />

# CARINA — Suite de Documentation Technique
### Architecture Système, Intégration Matérielle et Cadre de Sécurité
*Noxfort Systems — A State Of Art Company*

[![Statut](https://img.shields.io/badge/Statut-Actif-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Traductions :** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Hub Central](../index.md)**

---

</div>

## Bienvenue dans la Documentation Technique Officielle

Ce répertoire contient la suite documentaire technique en **Français** pour **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — un écosystème d'apprentissage par renforcement profond pour entreprises conçu pour le contrôle distribué des feux de circulation urbains.

## Répertoire des Guides Techniques

| Document | Sujet | Contenu Clé |
|---|---|---|
| 📚 **[Index Maître Central (MOC)](carina_moc.md)** | Index Général & Graphe de Connaissances | Vue d'ensemble du codebase, hiérarchie architecturale des répertoires et graphe bidirectionnel Obsidian. |
| 📖 **[Architecture Système](architecture.md)** | Architecture Centrale | 8 microservices d'OS concurrents, propriétaire unique `CARINA_GATEWAY_ROLE`, ST-GATv2 Lite, iTransformer PAE et QR-D3QN. |
| 🚑 **[Préemption d'Urgence (EVP)](evp_and_preemption.md)** | Préemption pour Véhicules d'Urgence | Couloirs verts autonomes, cinématique Haversine ($60\text{--}160\text{ m}$), synchronisation inter-processus et passerelle Web protégée par jeton (port 2201). |
| 🔌 **[Pilotes Matériels & Passerelle Go](hardware_drivers.md)** | Contrôleurs de Terrain | Passerelle Go à propriétaire unique (`carina-go`), IPC par tube NDJSON, NTCIP 1202 (`.4.1.*`/`.5.1.*`), UTMC2, SNMPv3 USM, décodage d'étapes en boucle fermée et trappes binaires. |
| 🛡️ **[Architecture de Sécurité, Watchdog & FENIX](safety_and_watchdog.md)** | Sécurité Neuro-Symbolique | `PhysicalActionMasker`, règles symboliques (SR-00 à SR-06), calibration `CHILD` QR-D3QN + Noisy-OR, Watchdog et bascule en boucle fermée F.E.N.I.X. |
| ⚡ **[API Synapse HFT & Files IPC](api_reference.md)** | Interface Haute Fréquence | gRPC Synapse HFT (TLS/mTLS & authentification Bearer, port 50051), 12 files IPC bornées + 1 tube thread-safe et diffusion CCO épinglée. |
| 🗄️ **[Architecture de Base de Données & Schémas](database_and_schemas.md)** | Persistance & Schémas | Stockage delta PostgreSQL (**97.9% de réduction**), `PostgresConnectionPool`, SQLite WAL, SQL `make_interval` et rétention EVP sur 168 h. |
| 🧠 **[Recherche Neuronale & Formulations](research_notes.md)** | Modélisation Mathématique | TCN unifié (`GroupNorm` + `SiLU`), mise en lots `torch.vmap`, iTransformer PAE, QR-D3QN + Noisy-OR, ST-GATv2 CTDE et DA SILVA binaire ($\ln 2$). |
| 🚦 **[Mandats de Feux de Signalisation (MUTCD)](traffic_engineering_warrants.md)** | Ingénierie du Trafic | Évaluation algorithmique des mandats réglementaires formels de signalisation FHWA/MUTCD (Mandats 1 à 4 : Volume, Délai, File d'attente, Saturation). |
| 📈 **[MFD & Analyse du Trafic Réseau](mfd_and_analytics.md)** | Physique Macroscopique | Régressions du diagramme fondamental macroscopique (MFD), atténuation de la chute de capacité, régulation de périmètre (*perimeter gating*) et cache de filtres d'incidents. |
| 🔍 **[IA Explicable (XAI) & SAS](xai_and_sas.md)** | Audit Municipal & XAI | Gradients intégrés Google Captum (pipeline multi-agents mis en cache), 5 équations formelles et moteur d'audit médico-légal des vetos du Guardian. |
| 📄 **[Moteur de Blocs de Rapports](report_blocks_and_templates.md)** | Rapports Automatisés | Génération Word (.docx) conforme à l'ABNT NBR 14724 avec équations OMML et `ReportNumberFormatter` avec mise en cache par stat. |
| 🤖 **[Petits Modèles de Langage (SLM)](slm_and_local_llm.md)** | IA Privée Hors Ligne | Inférence locale Qwen3.5 2B / llama.cpp sérialisée via `slm_process_lock`, sondage VRAM `pynvml` et `unload()` explicite. |
| 🖥️ **[Interface Desktop & Vue de Planification](ui_and_dashboard.md)** | Architecture Frontend | IHM bureautique Flet, CCO React 18 (animations par compositeur & vue rAF), mise en pause sur fenêtre masquée `MapAnimator` et `AuditLogWidget` paginé. |
| 🗺️ **[Rendu de Carte Vectorielle & Cartes Thermiques](rendering_and_heatmaps.md)** | Visualisation Géospatiale | Cache LRU SUMO `.net.xml` (`read_sumo_net_cached`), rendu hors écran `mpl_utils` et cartes thermiques KDE asynchrones. |
| 🔐 **[Sécurité & Authentification](security_and_auth.md)** | Gouvernance & Accès | RBAC, verrouillage PBKDF2 salé, gRPC TLS/mTLS & authentification Bearer, passerelle Web fail-closed `503` et épinglage de certificat SHA-256. |
| 🛠️ **[Guides du Développeur](developer_guides.md)** | Ingénierie & Extension | `.env` 12-Factor & paramètres `[SYNAPSE]`, `CARINA_GATEWAY_ROLE`, protocoles ségrégués `src/interfaces/` et agents personnalisés. |
| 🧪 **[Tests & Assurance Qualité](testing.md)** | QA & Suite de Tests | **967 tests Pytest** (935 unitaires, 18 d'intégration, 14 à la racine), **46 tests unitaires Go**, `scripts/pytest_limited.sh` et `tests/memory_guard.py`. |
| 🚀 **[Déploiement & Empaquetage](deployment_and_packaging.md)** | Opérations & Empaquetage | Builds Docker multi-étapes, démons Systemd, passerelle Web fail-closed zéro confiance et déploiement Tailscale Funnel. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
