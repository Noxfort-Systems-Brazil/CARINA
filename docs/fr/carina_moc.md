---
tags: [moc, hub, docs, obsidian, carina, index]
aliases: [CARINA MOC, Hub de Documentation Maître, Index de Documentation, Coffre de Connaissances]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="Logo CARINA CORE" width="120" />

# Hub de Documentation Maître Technique CARINA
### Index Central & Coffre de Connaissances de l'Architecture Multi-Agents
*Noxfort Systems — A State Of Art Company*

</div>

Bienvenue dans la bibliothèque de documentation technique de **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture). Conçu comme un écosystème d'apprentissage par renforcement profond massivement concurrent et haute fréquence pour le contrôle en temps réel des feux de circulation, CARINA fait le pont entre une IA neuro-symbolique de haut niveau, l'actionnement matériel gRPC en temps réel et l'isolation multiprocessus au niveau du système d'exploitation.

Cet index documentaire maître offre une couverture technique approfondie pour les développeurs du noyau, les chercheurs académiques, les ingénieurs municipaux de la circulation et les intégrateurs de systèmes. Il est entièrement compatible avec **GitHub** et **[Obsidian](https://obsidian.md/)**.

---

## 🗺️ Carte du Codebase & Hiérarchie des Répertoires

```text
CARINA_CORE/
├── carina.py                   # Orchestrateur Maître (SingleInstanceLock, ProcessManager, UI/Tray)
├── ARCHITECTURE.md             # Schéma directeur à 8 processus et topologie IPC
├── pyproject.toml              # Chaîne d'outils de compilation & métadonnées du projet
├── requirements.txt            # Dépendances d'exécution Python
├── .env.example                # Variables d'environnement & identifiants 12-Factor App
│
├── config/                     # Systèmes de Configuration
│   ├── settings.ini            # Paramètres globaux (IA, PBT, Watchdog, MFD, Journalisation)
│   ├── database/               # Requêtes SQL dynamiques & schémas (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Règles de sécurité et cohérence sémantique (safety_rules.json, semantic_rules.json)
│   └── templates/              # Modèles multilingues de rapports, MFD, SAS & XAI
│
├── proto/                      # Spécifications de Protocoles gRPC
│   └── synapse_hft.proto       # Définitions Protobuf de télémétrie & d'actionnement haute fréquence
│
├── docs/                       # Coffre Exhaustif de Connaissances
│   ├── CARINA_MOC.md           # Hub Maître de Documentation (Ce Fichier)
│   ├── index.md                # Point d'entrée & portail MkDocs
│   ├── ARCHITECTURE.md         # Schéma directeur à 8 processus et topologie IPC
│   ├── EVP_AND_PREEMPTION.md   # Préemption pour Véhicules d'Urgence, Passerelle Web Go & CCO
│   ├── API_REFERENCE.md        # Protocole gRPC Synapse HFT & schémas de files IPC
│   ├── RESEARCH_NOTES.md       # Formulations mathématiques PPO-TCN, PAE, GATv2 & DA SILVA
│   ├── HARDWARE_DRIVERS.md     # Contrôleurs Physiques : NTCIP 1202, UTMC2 & intégration SNMP
│   ├── SAFETY_AND_WATCHDOG.md  # Pare-feu de Sécurité Guardian, Règles de Veto & Watchdog
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # Mandats de Feux MUTCD / FHWA 1, 2, 3, 7, 8
│   ├── MFD_AND_ANALYTICS.md    # Diagramme Fondamental Macroscopique & Dynamique de Densité Réseau
│   ├── DATABASE_AND_SCHEMAS.md # Niveau de Persistance, Stockage Delta Asynchrone & Schémas SQL
│   ├── XAI_AND_SAS.md          # IA Explicable, Gradients Intégrés Captum & Analyses SAS
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # Constructeur Word ABNT (.docx) & Équations Mathématiques OMML
│   ├── SLM_AND_LOCAL_LLM.md    # Intégration de LLM Local Hors Ligne (Qwen3 1.7B / llama.cpp)
│   ├── UI_AND_DASHBOARD.md     # Application Desktop Flet, Vue de Planification & Architecture SDS
│   ├── RENDERING_AND_HEATMAPS.md # Rendu de Carte Vectorielle & Interpolation Asynchrone de Cartes Thermiques
│   ├── SECURITY_AND_AUTH.md    # Comptes Utilisateurs, Hachage Bcrypt Salé & Verrouillage Anti-Force Brute
│   ├── DEVELOPER_GUIDES.md     # Configuration Environnement, Hiérarchie d'Agents, Paramètres & Empaquetage
│   ├── TESTING.md              # Suite de Tests Pytest, Mocks de Pilotes & Validation de Couverture
│   └── DEPLOYMENT_AND_PACKAGING.md # Builds Docker, Démons Systemd & Paquets Debian
│
├── bin/                        # Binaires natifs compilés (carina-go)
├── src_go/                     # Passerelle Matérielle & Web en Go (NTCIP, UTMC, EVP, Passerelle Web)
│   ├── cmd/gateway/            # Point d'entrée de la passerelle & boucle IPC stdin/stdout NDJSON
│   ├── configs/                # Profils JSON OID intégrés NTCIP & UTMC
│   ├── evp_go/                 # Répartiteur de Préemption EVP à la microseconde
│   ├── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
│   └── web_gateway/            # Passerelle HTTP/SSE (Port 2201), Réseau Maillé Tailscale & Gestionnaires CCO
├── src_tsx/                    # Application Web Central Control Operator (CCO)
│   └── src_cco/                # React 18, TypeScript, Tailwind CSS, Calques Cartographiques SVG, ECharts
├── src/                        # Code Source Principal
│   ├── agents/                 # PPO LocalAgent, GuardianAgent & StrategistAgent
│   ├── analysis/               # WarrantEvaluator MUTCD, WarrantMath & Analyse de Trafic
│   ├── blocks/                 # Constructeur modulaire .docx, convertisseurs OMML & nettoyeurs de texte
│   ├── central_controller.py   # Serveur de Télémétrie gRPC Haute Fréquence
│   ├── communication/          # MonitorClient, serveur HFT & ponts de télémétrie externe
│   ├── controller/             # ConnectionManager, FailSafeManager, StageValidator & Dérogations
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, ActionAuthorizer & PopulationManager
│   ├── database/               # DatabaseEngine, DatabaseWorker & StepDecisionWorker
│   ├── drivers/                # Proxy Python Go Gateway, DriverFactory, IncidentReporter & IncidentFilter
│   ├── engine/                 # EpisodeRunner, StepProcessor, Optimiseurs & Entraîneurs PPO/DQN
│   ├── evp/                    # Préemption de Véhicules d'Urgence (EVPService, Cinématique, PreemptionEngine)
│   ├── fenix/                  # Auto-Guérison F.E.N.I.X. & Superviseur de Processus (Supervisor, Runner, Reconciler)
│   ├── handlers/               # Requêtes IA, commandes d'interface & gestionnaires de commandes Watchdog
│   ├── launcher/               # ProcessManager, SingleInstanceLock & UITrayManager
│   ├── maturity/               # MaturityManager, AgentMaturity, PromotionService, Config & Port
│   ├── mfd/                    # Analyseur & Worker du Diagramme Fondamental Macroscopique (MFD)
│   ├── models/                 # Architectures Neuronales (PAE, TCN, ST-GATv2 Lite, CrossAttention)
│   ├── promotion/              # MaturityPacingCalculator, PerformanceMarginCalculator & PromotionEvaluator
│   ├── rendering/              # StaticMapRenderer & AsyncHeatmapRenderer
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo & CloudVaultRepo
│   ├── safety/                 # Processus GuardianWorker & routage des signaux IPC
│   ├── sas/                    # Smart Analysis System (Mandats d'Infrastructure Hors Ligne)
│   ├── sds/                    # Smart Dashboard Service (Pont UI Flet & WebSockets)
│   ├── settings/               # Paramètres Modulaires (Interfaces SOLID, schémas, INI & .env)
│   ├── slm/                    # Petit Modèle de Langage (Inférence hors ligne Qwen3 / llama.cpp)
│   ├── transports/             # Transports polymorphes (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Chemins & Sous-système de Sécurité
│   │   └── security/           # AuthService, UserService, Hacheur Bcrypt & LockdownManager
│   ├── watchdog/               # Moniteur de pulsation de processus temps réel & repli fail-safe
│   └── xai/                    # Attribution par Gradients Intégrés, constructeur de rapports & worker
│
├── ui/                         # Application Desktop Native Flet
│   ├── cards/                  # Cartes modulaires de paramètres & télémétrie (MonitorSettingsCard)
│   ├── handlers/               # Gestionnaires d'événements, SettingsHandler & SystemTrayHandler natif
│   ├── views/                  # DashboardView, PlanningView, DiagnosticsView, SettingsView
│   ├── widgets/                # LiveCanvasMapWidget, PlanningControlPanel, MFDViewer, XAIViewer
│   ├── renderers/              # PlanningMapRenderer, MapVisualSyncer, MapDrawer
│   ├── animators/              # MapAnimator & contrôleurs de transition
│   └── locales/                # Dictionnaires JSON multilingues (pt_br, en_us, es_es, etc.)
│
└── tests/                      # Suite de Tests Pytest (Unitaires, Intégration & Mocks Matériels)
```

---

## 📖 Dimensions du Système & Navigation dans le Coffre de Connaissances

### 1. Infrastructure Centrale & Pilotes Matériels
- **[Architecture Détaillée](architecture.md)** : Schéma directeur technique exhaustif détaillant les 8 microservices OS concurrents, l'isolation des processus par `multiprocessing`, les canaux IPC Pipes/Files et la boucle d'exécution.
- **[Pilotes Matériels & Contrôleurs Physiques](hardware_drivers.md)** : Spécifications pour la passerelle matérielle Go compilée (`carina-go`), l'IPC par tubes anonymes standards NDJSON, NTCIP 1202 (ASC), la norme britannique UTMC / UTMC2, le client SNMP v2c/v3, le pool de connexions et la réversion de sécurité matérielle déterministe.
- **[Référence API & Protocole HFT](api_reference.md)** : Spécifications complètes pour l'interface gRPC `Synapse HFT`, la télémétrie externe Monitor (MQTT/HTTP), les points de terminaison métriques Prometheus (port 8001) et les schémas de files IPC.
- **[Architecture de Base de Données & Schémas](database_and_schemas.md)** : Spécifications pour `DatabaseWorker`, `StepDecisionWorker`, le pool de connexions, la configuration 12-Factor `.env` et le stockage delta PostgreSQL (réduction de 97.9%).
- **[Sécurité & Authentification](security_and_auth.md)** : Gestion des comptes utilisateurs, hachage `bcrypt` avec sel, défense par verrouillage anti-force brute et contrôle d'accès basé sur les rôles.
- **[Architecture Modulaire des Paramètres](architecture.md#4-architecture-modulaire-des-parametres-srcsettings)** : Sous-système de configuration SOLID découplant schémas, persistance INI et secrets 12-Factor `.env`.
- **[Surveillance Polymorphe & Transports](architecture.md#5-surveillance-polymorphe--architecture-de-transport-srctransports)** : Télémétrie et flux d'incidents via courtiers MQTT et points de terminaison cloud HTTP/HTTPS REST/Ngrok.

### 2. Intelligence Artificielle & Sécurité Neuro-Symbolique
- **[Recherche Neuronale & Formulations](research_notes.md)** : Formulations mathématiques approfondies pour PPO-TCN, projection latente $Z$ de l'auto-encodeur prédictif (PAE), flux de valeur/avantage Dueling DQN-TCN, attention sur graphes ST-GATv2 Lite et programme pédagogique de maturation DA SILVA.
- **[Architecture de Sécurité, Watchdog & F.E.N.I.X.](safety_and_watchdog.md)** : Inventaire des règles de veto symbolique (SR-01 à SR-05), seuils de veto neuronal PAE, surveillance de pulsation temps réel par Watchdog (< 500 ms) et résurrection autonome de processus F.E.N.I.X. avec réconciliation d'état aux frontières propres.
- **[IA Explicable, SAS & Analyses MFD](xai_and_sas.md)** : Détails opérationnels du pipeline modulaire XAI, attribution par gradients intégrés de Captum et audits municipaux médico-légaux.
- **[Moteur de Blocs de Rapports & Générateur Word](report_blocks_and_templates.md)** : Génération automatisée de rapports Word (`.docx`) conformes à l'ABNT NBR 14724 avec formules LaTeX natives en Office Math Markup Language (OMML).
- **[Petits Modèles de Langage (SLM)](slm_and_local_llm.md)** : Inférence LLM locale 100% hors ligne (Qwen3 1.7B / llama.cpp) générant des justifications textuelles médico-légales sans dépendances cloud.

### 3. Physique du Trafic, Mandats & Graphiques
- **[Mandats de Feux de Signalisation en Ingénierie du Trafic](traffic_engineering_warrants.md)** : Évaluation automatisée des mandats de feux réglementaires formels MUTCD / FHWA (Mandats 1, 2, 3, 7, 8) et des mandats d'infrastructure.
- **[Diagramme Fondamental Macroscopique & Dynamique](mfd_and_analytics.md)** : Physique de flux-densité à l'échelle du réseau, densité critique ($K_{crit}$), régulation de périmètre (*perimeter gating*), détection de chute de capacité et mise en cache des filtres d'incidents.
- **[Rendu de Carte & Cartes Thermiques](rendering_and_heatmaps.md)** : Analyse de carte vectorielle hors ligne à partir des réseaux SUMO `.net.xml` et cartes thermiques asynchrones par estimation de densité par noyau (KDE).

### 4. Interface Desktop & Opérations
- **[Interface & Service de Tableau de Bord Intelligent](ui_and_dashboard.md)** : Décomposition architecturale de l'IHM bureautique native Flet, vue de planification, verrouillage par socket d'instance unique (port 42123) et flux de télémétrie par WebSocket.
- **[Guides du Développeur & Intégration](developer_guides.md)** : Guide pour configurer l'environnement, modifier les configurations, étendre les agents et construire les paquets.
- **[Tests & Validation](testing.md)** : Directives pour exécuter `pytest`, générer des rapports de couverture (`--cov=src`), simuler les contrôleurs et valider les vetos de sécurité Guardian.
- **[Déploiement, Empaquetage & Conteneurisation](deployment_and_packaging.md)** : Guide pour la conteneurisation Docker (`Dockerfile`), unités de service Systemd et paquets Debian `.deb`.

### 5. Préemption d'Urgence & Opérations Distantes (EVP / CCO)
- **[Préemption pour Véhicules d'Urgence & Opérations Distantes](evp_and_preemption.md)** : Spécifications pour le moteur de préemption de véhicules d'urgence (EVP), conformité CONTRAN/MUTCD, cinématique Haversine, déclenchement à deux facteurs, repli de sécurité Watchdog de 45 secondes, répartiteur de préemption Go, réseau maillé sécurisé Tailscale Funnel et interface web Central Control Operator (CCO) (`src_tsx/src_cco`).

---

> 💡 **Graphe de Connaissances Obsidian :** Cette suite documentaire offre un support natif complet pour [Obsidian](https://obsidian.md/). Ouvrez le dossier du dépôt `CARINA_CORE` en tant que coffre Obsidian pour naviguer dans le graphe technique interactif et les liens rétrospectifs.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
