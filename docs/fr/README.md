<div align="center">

# CARINA — Suite de Documentation Technique
### Architecture Système, Intégration Matérielle et Sécurité Neuro-Symbolique
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Actif-brightgreen?style=flat&logo=github)](https://github.com/Noxfort/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Traductions / Langues :** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Hub Central](../README.md)**

---

</div>

## Bienvenue dans la Documentation Technique Officielle

Ce répertoire contient la suite documentaire technique en **Français** pour **CARINA** (Cognitive Autonomous Real-time Intersection Network Architecture) — un écosystème d'apprentissage par renforcement profond distribué pour le contrôle adaptatif des feux de circulation en temps réel.

## Répertoire des Guides Techniques

| Document | Sujet | Contenu Principal |
|---|---|---|
| 📖 **[Architecture Système](architecture.md)** | Architecture Centrale | 8 microservices OS concurrents, attention spatio-temporelle ST-GATv2 Lite, Agent Consultant PAE (128 canaux) et accélération AMP/TensorCores. |
| 🔌 **[Contrôleurs et Passerelle Go](hardware_drivers.md)** | Contrôleurs de Feux | Passerelle Go compilée (`carina-go`), communication IPC via tubes anonymes NDJSON (zéro port ouvert), protocoles NTCIP 1202, UTMC2 et repli de sécurité atomique. |
| 🛡️ **[Sécurité, Watchdog et FENIX](safety_and_watchdog.md)** | Sécurité Neuro-Symbolique | Règles de veto symbolique (SR-01 à SR-05), veto neural D3QN Guardian contre l'engorgement, Watchdog temps réel (< 500 ms) et résilience F.E.N.I.X. |
| ⚡ **[API Synapse HFT et Files IPC](api_reference.md)** | Interface Haute Fréquence | Interface gRPC Synapse HFT (port 50051), 10 canaux de communication inter-processus et passerelle télémétrique polymorphe (MQTT et HTTP/REST). |
| 🗄️ **[Base de Données et Stockage Delta](database_and_schemas.md)** | Persistance et Schémas | Moteur de stockage asynchrone avec compression delta sous PostgreSQL (**97.9% de réduction d'espace disque**), énumérations Smallint 1 octet et 12-Factor `.env`. |
| 🧪 **[Tests et Assurance Qualité](testing.md)** | Validation et Tests | Suite de tests Pytest (53 modules unitaires), tests natifs en Go (`go test`), validation des vetos de sécurité et couverture de code. |
| 🔍 **[IA Explicable (XAI) et SAS](xai_and_sas.md)** | Audit Légal Municipal | Google Captum Integrated Gradients, les 5 équations mathématiques formelles et génération automatique de rapports Word (.docx) conformes aux audits. |

---

<div align="center">
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de la Mobilité Intelligente • CARINA CORE v1.2.0</i>
</div>
