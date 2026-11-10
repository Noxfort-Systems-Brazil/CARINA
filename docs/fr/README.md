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
| 📖 **[Architecture Système](architecture.md)** | Architecture Centrale | 8 microservices d'OS concurrents, attention sur graphes ST-GATv2 Lite, Universal PAE et accélération Universal AMP. |
| 🚑 **[Préemption d'Urgence (EVP)](evp_and_preemption.md)** | Préemption pour Véhicules d'Urgence | Couloirs verts autonomes, portes cinématiques d'entrée/sortie Haversine ($60\text{--}160\text{ m}$), passerelle Web Tailscale (port 2201) et mur d'écrans CCO en React. |
| 🔌 **[Pilotes Matériels & Passerelle Go](hardware_drivers.md)** | Contrôleurs de Terrain | Passerelle matérielle industrielle en Go (`carina-go`), IPC par tube anonyme NDJSON sans port, NTCIP 1202, UTMC2, pool de clients SNMP et basculement de sécurité atomique. |
| 🛡️ **[Architecture de Sécurité, Watchdog & FENIX](safety_and_watchdog.md)** | Sécurité Neuro-Symbolique | Règles de veto symbolique (SR-01 à SR-05), vetos anti-engorgement D3QN Guardian, Watchdog temps réel (< 500 ms) et auto-résurrection F.E.N.I.X. |
| ⚡ **[API Synapse HFT & Files IPC](api_reference.md)** | Interface Haute Fréquence | Interface gRPC sous-milliseconde Synapse HFT (port 50051), 10 canaux IPC bornés et transports télémétriques polymorphes. |
| 🗄️ **[Architecture de Base de Données & Schémas](database_and_schemas.md)** | Persistance & Schémas | Moteur de stockage delta asynchrone PostgreSQL réalisant **97.9% de réduction de stockage**, enums Smallint sur 1 octet et `.env` 12-Factor. |
| 🧠 **[Recherche Neuronale & Formulations](research_notes.md)** | Modélisation Mathématique | Convolutions temporelles PPO-TCN, projections latentes PAE, Dueling DQN, ST-GATv2 Lite et programme pédagogique DA SILVA. |
| 🚦 **[Mandats de Feux de Signalisation (MUTCD)](traffic_engineering_warrants.md)** | Ingénierie du Trafic | Évaluation algorithmique des mandats réglementaires formels de signalisation FHWA/MUTCD (Mandats 1, 2, 3, 7, 8). |
| 📈 **[MFD & Analyse du Trafic Réseau](mfd_and_analytics.md)** | Physique Macroscopique | Régressions du diagramme fondamental macroscopique (MFD), atténuation de la chute de capacité, régulation de périmètre (*perimeter gating*) et cache de filtres d'incidents. |
| 🔍 **[IA Explicable (XAI) & SAS](xai_and_sas.md)** | Audit Municipal & XAI | Gradients intégrés Google Captum, 5 équations mathématiques formelles et moteur d'audit médico-légal des vetos du Guardian. |
| 📄 **[Moteur de Blocs de Rapports](report_blocks_and_templates.md)** | Rapports Automatisés | Génération de documents Word (.docx) conformes à l'ABNT NBR 14724 avec équations natives en Office Math Markup Language (OMML). |
| 🤖 **[Petits Modèles de Langage (SLM)](slm_and_local_llm.md)** | IA Privée Hors Ligne | Inférence LLM locale 100% hors ligne (Qwen3 1.7B / llama.cpp) générant des explications textuelles médico-légales sans fuite vers le cloud. |
| 🖥️ **[Interface Desktop & Vue de Planification](ui_and_dashboard.md)** | Architecture Frontend | IHM bureautique native Flet, vue de planification vectorielle interactive, gestion dans la zone de notification (*system tray*) et verrouillage d'instance unique (port 42123). |
| 🗺️ **[Rendu de Carte Vectorielle & Cartes Thermiques](rendering_and_heatmaps.md)** | Visualisation Géospatiale | Analyseur vectoriel hors ligne SUMO `.net.xml` et cartes thermiques asynchrones en temps réel par estimation de densité par noyau (KDE). |
| 🔐 **[Sécurité & Authentification](security_and_auth.md)** | Gouvernance & Accès | Contrôle d'accès basé sur les rôles (RBAC), hachage salé bcrypt, verrouillage anti-force brute et isolation 12-Factor. |
| 🛠️ **[Guides du Développeur](developer_guides.md)** | Ingénierie & Extension | Configuration de l'environnement, implémentation d'agents neuronaux personnalisés et architecture de paramètres modulaires SOLID. |
| 🧪 **[Tests & Assurance Qualité](testing.md)** | QA & Suite de Tests | Suite Pytest avec 647 tests automatisés, tests unitaires natifs en Go (`go test`), simulations de sécurité Guardian et validation de couverture. |
| 🚀 **[Déploiement & Empaquetage](deployment_and_packaging.md)** | Opérations & Empaquetage | Conteneurisation Docker multi-étapes avec accélération CUDA et unités de démons Linux Systemd. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
