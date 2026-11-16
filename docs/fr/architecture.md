---
tags: [architecture, core, system, gatv2, pae, pbt, amp, multiprocessing]
aliases: [Architecture Système, Schéma Multiprocessus, Vue d'Ensemble du Système]
---

# 🏛️ CARINA : Schéma Directeur du Système & Architecture Multiprocessus

Ce document spécifie l'architecture d'ingénierie interne de l'écosystème CARINA. Il détaille les 8 microservices concurrents du système d'exploitation, la topologie canonique des réseaux neuronaux profonds (LocalAgent PPO-TCN, GuardianAgent D3QN et StrategistAgent ST-GATv2 Lite), le `TopologicalScaler`, les pilotes de contrôleurs physiques et le moteur asynchrone de stockage delta sous PostgreSQL.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🧠 Voir [Formulations Neuronales](research_notes.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md)

---

## 1. Modèle de Concurrence des Microservices Multiprocessus

Le Verrou Global de l'Interpréteur Python (GIL) empêche l'inférence IA multi-thread dépendante du processeur et les opérations d'E/S lourdes de s'exécuter en véritable parallélisme. Pour atteindre une latence d'actionnement inférieure à la milliseconde, CARINA utilise un **modèle de microservices multiprocessus** orchestré par [`carina.py`](../../carina.py) et [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py) (modularisé avec [`backend_service_registry.py`](../../src/launcher/backend_service_registry.py), [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py) et [`worker_entrypoints.py`](../../src/launcher/worker_entrypoints.py)), combiné à une **Passerelle Matérielle & Web Go** de qualité industrielle (`bin/carina-go`) détenue exclusivement par `CentralController` (`CARINA_GATEWAY_ROLE=owner`) :

```mermaid
graph TD
    Launcher[carina.py Orchestrateur / Tray IHM - remote] -->|Génère & Surveille| PM[ProcessManager]

    PM --> CC[1. Processus CentralController - owner]
    PM --> AI[2. Moteur AI_Process - remote]
    PM --> WD[3. Processus Watchdog]
    PM --> SDS[4. DashboardService SDS - remote]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Moteur MFD_Worker]

    CC <-->|ThreadSafePipeConnection| AI
    CC -->|File wd Heartbeats| WD
    WD -->|File fenix| PM
    AI -->|File db| DB
    CC -->|File sds| SDS
    CC -->|File sas| SAS
    CC -->|File mfd_trigger| MFD
    MFD -->|File mfd_results| CC
    SAS -->|File sas_results| CC
    XAI -->|Journaux Disque HFT| AI

    CC <-->|Stdin/Stdout NDJSON| GW[Passerelle Go carina-go]
    GW --> NTCIP[Contrôleurs NTCIP 1202 / UTMC2 UDP 161]
    GW --> WebGW[Passerelle Web Go Port 2201 / TLS / Tailscale]
    WebGW --> CCO[Carte Web CCO React/TSX src_tsx]
    WebGW <--|Télémétrie POST 204 Jeton Auth| EVP[Antennes GPS EVP Port 8085 / 2201]
```

### 1.1 Propriétaire Unique de la Passerelle (`CARINA_GATEWAY_ROLE`) & Synchronisation Matérielle en Boucle Fermée
Pour éviter le *split-brain* d'interrogation SNMP, les conflits sur le port `162` des trappes et les processus enfants `carina-go` en double entre les workers multiprocessus :
- **Processus Propriétaire (`CARINA_GATEWAY_ROLE=owner`) :** Défini strictement dans [`execute_controller_process`](../../src/launcher/worker_entrypoints.py) pour `CentralController`. Il démarre [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (composé de `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` et `TailscaleGatewayAdapter`), qui détient exclusivement `bin/carina-go`, les connexions SNMP locales de `HardwareConnectionManager` et l'ingestion de télémétrie `EVPService`.
- **Processus Miroirs Distants (`CARINA_GATEWAY_ROLE=remote`) :** Défini dans [`carina.py`](../../carina.py), [`src/main.py`](../../src/main.py) (`AI_Process`) et [`dashboard_worker.py`](../../src/sds/dashboard_worker.py). Les processus distants synchronisent l'état en miroir via IPC (`RemoteHardwareDriverProxy` via [`remote_proxy_synchronizer.py`](../../src/drivers/remote_proxy_synchronizer.py)) et transfèrent les actions/préemptions (`ai_hardware_cmd`, `ai_evp_preempt`, `set_hardware_connection`) à travers [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Télémétrie Matérielle en Boucle Fermée (`HardwareTelemetrySynchronizer`) :** Dans la boucle d'IA, [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) et [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) décodent en direct les masques de bits des signaux NTCIP 1202 / UTMC2 (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) en indices de phase SUMO à base 0 pour un véritable contrôle en boucle fermée et la réconciliation de bascule F.E.N.I.X.

---

## 2. Architecture Avancée d'Apprentissage Profond

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │   Auto-détection Nœuds (N) -> Dim Latente (32/64/128/256), Têtes (2/4/8/16)│
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │      LOCAL AGENT (PPO)      │           │   STRATEGIST AGENT (GRAPH)  │
     │  Tronc Dorsal Tactique TCN  │           │   Coordinateur ST-GATv2 Lite│
     │  (Actionnement Sous-Seconde)│◄──────────┤   (Ondes Vertes Artérielles)│
     └──────────────┬──────────────┘Vect Contexte└────────────┬──────────────┘
                    │                                         │
                    │ Action Proposée                         │ Contexte Réseau
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │  Bouclier Neuro-Symbolique, Prévention de Remontée de File & Veto Trafic│
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 Module ST-GATv2 Lite (`src/models/st_gatv2_lite.py` & `src/engine/strategic_coordinator.py`)
- **Finalité :** Synchronisation spatiale des « Ondes Vertes » artérielles sur les carrefours voisins du graphe de réseau routier urbain à l'aide de `TemporalConvNetLite` (`GroupNorm(1, C)` + `SiLU` + `TemporalAttentionPool`) suivi de deux couches résiduelles `GATv2Conv`.
- **Têtes Auto-Supervisées en Ligne & CTDE :** Inclut une tête auxiliaire de prévision à un pas (`pred_head`) et une tête de valeur globale coopérative (`global_critic_head`). [`StrategicCoordinator`](../../src/engine/strategic_coordinator.py) agrège les séquences de nœuds via des appels non-mutants [`StateExtractor.peek_state()`](../../src/engine/state_extractor.py) afin que les lectures graphiques secondaires ne corrompent jamais les EMA de `HistoricalAggregator`.
- **Coordination Décentralisée :** Le Strategist calcule périodiquement le tenseur de contexte spatio-temporel sur le réseau et l'injecte aux agents Local via un filtrage résiduel tanh (`PAEStateAugmentor`), permettant l'émergence d'ondes vertes sans point de défaillance unique centralisé.

### 2.2 Auto-Encodeur Prédictif Universel iTransformer Action-Conditionné (`src/models/pae.py`)
- **Finalité :** Modèle du monde physique partagé à haute capacité projetant la dynamique spatio-temporelle future ($t + \Delta t$) sur des topologies de carrefours hétérogènes.
- **Architecture iTransformer & Incertitude :** Utilise RevIN par variable + plongement d'échelle `[mean, std]`, des couches d'encodeur Transformer inversées sur les variables de capteurs, un pooling latent par attention croisée avec `key_padding_mask` (`valid_dims`) pour que les voies rembourrées de zéros ne contaminent jamais les vecteurs latents, un conditionnement d'action binaire (`0 = ADVANCE`, `1 = KEEP`) et une estimation d'incertitude hétéroscédastique (`decode_with_uncertainty -> (mean, log_var)`), avec préchauffage optionnel via `torch.compile` (`torch_compile_helper.py`).
- **Encodage en Lots à Passe Unique :** Exécuté une fois par pas de simulation sur tous les carrefours via [`BatchedPAEEncoder`](../../src/engine/batched_pae_encoder.py) et réutilisé dans [`PPOOptimizer`](../../src/optimizer/ppo_optimizer.py) sur les époques de rollout via `precomputed_latents`.

### 2.3 Vectorisation Tactique & Sécurité Guardian Distributionnelle (`src/engine/`, `src/safety/`)
- **Tronc Dorsal TCN Causal Unifié (`src/models/tcn_backbone.py`) :** Remplace `weight_norm` déprécié par `TemporalConv1d`, une normalisation causale par canal `GroupNorm(1, C)`, `SiLU`, une initialisation orthogonale et `TemporalAttentionPool`. `ActorCriticNet` produit des logits FP32 bruts (`forward_logits`) masqués directement par [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py) (appliquant les contraintes de dégagement jaune/tout-rouge, vert minimal et vert maximal).
- **Inférence Homogène `torch.vmap` (`src/engine/fleet_batch_inferencer.py`) :** Regroupe les `LocalAgent` par signature architecturale et exécute des passes avant vectorisées via `torch.func.stack_module_state` + `torch.vmap`, compactant les scalaires dans des tampons NumPy CPU (`last_cpu_decisions`) et utilisant le GAE NumPy sur l'hôte dans `PPOOptimizer` ainsi que `ReplayMemory` / `StateReplayMemory` résidents sur CPU (`pin_memory`, cache `_max_priority` en $O(1)$, `push_batch`).
- **Guardian QR-D3QN Calibré & Noisy-OR (`src/safety/`) :** `D3QN_TCN` modélise `num_quantiles = 32` par action binaire pour le risque de queue $\text{CVaR}_{0.20}$. [`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py) normalise la saturation des tronçons entrants par rapport aux capacités réelles de véhicules par voie et projette sur l'horizon de dégagement $H = \text{yellow} + \text{all\_red}$ ; [`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py) effectue une calibration logistique optimisée en $F_2$ et une **fusion Noisy-OR** non compensatoire. [`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) entraîne le Guardian exclusivement pendant `Maturity.CHILD`, puis exécute `freeze_for_deployment()` à la promotion et persiste `guardian_{tl_id}.pth` via [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py).

### 2.4 Auto-Mise à l'Échelle Topologique en $O(1)$ (`src/utils/topo_scaler.py`)
- **Mise à l'Échelle Algorithmique :** Détecte automatiquement la densité du réseau ($N$ carrefours) et ajuste de manière autonome les dimensions neuronales en puissances de 2 optimisées pour les TensorCores NVIDIA :
  - $N \le 20 \implies \text{dim} = 32, \text{têtes} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{têtes} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{têtes} = 8$ (ex. Grille Métropolitaine de Londrina)
  - $N > 250 \implies \text{dim} = 256, \text{têtes} = 16$ (Grille Mégalopole)

### 2.5 Accélération Universelle AMP & TensorCore
- Toutes les passes avant des réseaux neuronaux sont enveloppées dans `torch.amp.autocast`, activant l'accélération matérielle native FP16/TF32 sur les TensorCores NVIDIA et limitant la consommation totale de VRAM à seulement **~20 Mo** pour les modèles centraux.

---

## 3. Données Persistantes & Moteur de Stockage Delta

CARINA implémente un moteur de persistance asynchrone utilisant la **Compression Delta par Plages** (*Run-Length Delta Compression*) et un pool de connexions thread-safe sous PostgreSQL et SQLite :
- **`step_decisions`** : Enregistre les suggestions, les vetos de sécurité Guardian et les durées d'étape expédiés via [`StepDecisionWorker`](../../src/database/step_decision_worker.py) dans des files de mémoire non-bloquantes (surcoût $< 0.001\text{ ms}$).
- **`edge_dictionary`** : Mappe les noms de voies longs sur des entiers de 4 octets pour un indexage compact.
- **Pool de Connexions & Pragmas (`src/database/connection_pool.py`) :** Fournit `PostgresConnectionPool` (`psycopg2.pool.ThreadedConnectionPool`, `minconn=1, maxconn=16`), une gestion déterministe de contexte `db_transaction`, le réglage SQLite WAL (`busy_timeout=30000`, `synchronous=NORMAL`, `temp_store=MEMORY`, `journal_mode=WAL`), le mode optionnel `enable_step_worker=False` pour les workers en lecture seule (`XaiWorker`), des requêtes paramétrées `make_interval(...)` et la purge automatisée de télémétrie EVP sur 168 heures.
- **Réduction de Stockage :** Permet une **réduction d'empreinte disque de 97.9%** (~380 Mo/jour pour un réseau métropolitain de 200 carrefours).

Pour les schémas de base de données et les requêtes détaillées, voir [Architecture de Base de Données & Schémas](database_and_schemas.md).

---

## 4. Architecture Modulaire des Paramètres (`src/settings/`)

Pour respecter les principes de **Responsabilité Unique** et de **Ségrégation des Interfaces** (SOLID), la gestion de la configuration de CARINA est décomposée en composants découplés et testables :

```text
       ┌────────────────────────────────────────────────────────┐
       │               SettingsService (Orchestrateur)          │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(Validation &  │     │& Write       │ │(settings.ini   │ │(Secrets d'Env .env   │
│ Plan Sections)│     │(Interfaces)  │ │ E/S Fichier)   │ │ 12-Factor App)       │
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ Façade de Rétrocompatibilité
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`) :** Registre faisant autorité pour mapper clés-sections (incluant les clés TLS/jeton gRPC `[SYNAPSE]` et les clés TLS/CORS/port `[REMOTE_GATEWAY]`), valeurs de repli par défaut et validation des types.
- **`IniFileStorage` (`src/settings/ini_storage.py`) :** Gère la lecture et l'écriture persistante dans `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`) :** Résout les secrets sensibles d'infrastructure depuis `.env` via `python-dotenv` avec analyse de fichier de secours (incluant `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN`, `CARINA_GATEWAY_TLS_*`, `CARINA_GATEWAY_PORT`, `CARINA_TRAP_PORT`).
- **`SettingsService` (`src/settings/service.py`) :** Service central orchestrant la récupération, validation et sérialisation de la configuration.
- **`SettingsManager` (`src/utils/settings_manager.py`) :** Façade rétrocompatible garantissant zéro régression pour le code appelant existant.
- **Protocoles SOLID (`src/interfaces/`) :** Interfaces ségréguées dans `controller.py`, `drivers.py`, `engine.py` et `repositories.py` découplant les couches coordinateur, passerelle, pilote, PAE, masquage d'actions et persistance.

---

## 5. Surveillance Polymorphe & Architecture de Transport (`src/transports/`)

CARINA intègre une **couche polymorphe de transport de télémétrie et d'incidents** permettant la surveillance à distance en temps réel via des courtiers MQTT locaux, des webhooks distants, des API REST Cloud ou des tunnels sécurisés (ex. Ngrok) :

```text
IncidentReporter / TelemetryLoop
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (Façade Singleton)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (Usine avec Résolution Automatique de Point de Terminaison)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│ (Courtier Local / Réseau) │             │ (API REST / Cloud / Ngrok)│
│ - Hôte:Port (ex. :1883)   │             │ - http:// ou https://     │
│ - Télémétrie QoS 0/1      │             │ - Session HTTP Persistante│
│ - Canaux: noxfort/telem/  │             │ - Retentative exponentielle│
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 Abstraction de Transport (`BaseMonitorTransport`)
Définit le contrat strict pour tous les exportateurs de télémétrie externe :
- `setup()` : Configure points de terminaison, délais et identifiants.
- `ensure_connected()` : Établit ou valide la connectivité.
- `publish(topic, payload)` : Transmet les charges JSON de manière asynchrone ou dans des threads de travail dédiés.
- `disconnect()` : Vide les tampons en attente et termine proprement les sessions.

### 5.2 Résolution Automatique de Point de Terminaison (`endpoint_resolver.py`)
Classifie intelligemment les points d'accès cibles sans exiger de configuration explicite de protocole :
- Les URL commençant par `http://` ou `https://` (ou les domaines contenant `ngrok`, `run.app` ou `/api/`) instancient `MonitorHttpTransport`.
- Les chaînes d'hôte standard ou adresses IP (`localhost`, `10.0.0.1`, `broker:1883`) instancient `MonitorMqttTransport`.

### 5.3 Déduplication des Incidents & Filtrage des Alertes (`src/drivers/`)
- [`IncidentReporter`](../../src/drivers/incident_reporter.py) diffuse les changements d'état des connexions matérielles et les erreurs de contrôleurs vers les outils externes de supervision.
- [`IncidentFilter`](../../src/drivers/incident_filter.py) élimine les tempêtes d'alertes en mettant en cache les hachages d'incidents actifs avec un filtrage temporel anti-rebond, persistant `.carina_incident_filter_cache.json` à travers les redémarrages.

---

## 6. Passerelle Matérielle de Terrain Haute Performance (`src_go/`)

Pour atteindre une fiabilité de niveau industriel, un déterminisme réseau inférieur à la milliseconde et éliminer la contention du GIL sur le terrain, CARINA délègue toutes les communications avec les contrôleurs physiques de feux (ports UDP 161 et 162) à une **Passerelle Matérielle Go** compilée (`bin/carina-go` construite à partir de `src_go/`) :

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │   [Synapse Perception]  <-- gRPC (50051) -->  [Caméra] │
       │            │                                           │
       │      [Moteur IA / NN]                                  │
       │            │                                           │
       │     [ActionSupervisor]                                 │
       │            │                                           │
       │ [HardwareConnectionManager] (Orchestrateur Python)     │
       │            │                                           │
       │    [GoGatewayClient] (Gestionnaire Sous-Processus Tube)│
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout (JSON Délimité par Retours à la Ligne)
                    │ ZÉRO PORT RÉSEAU OUVERT SUR L'HÔTE
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │         PASSERELLE MATÉRIELLE CARINA (Démon Go)        │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [Scanneur IPC NDJSON & Écrivain Concurrent]       │
       │  +-- [Registre de Connexions HardwareManager]          │
       │  +-- [Fail-Safe Atomique sur EOF / SIGPIPE]            │
       │  +-- [Moteur de Pulsation : time.Ticker par carrefour] │
       │  +-- [Répartiteurs de Protocoles NTCIP 1202 & UTMC2]   │
       │  +-- [Pool de Clients GoSNMP (UDP 161)]                │
       │  +-- [Serveur TrapListener (UDP 162)]                  │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Trappes)
                            ▼                  ▼
                    [Contrôleur Terrain] [Contrôleur Terrain] ...
```

### 6.1 Propriétés Architecturales Clés
- **Propriété par Processus Unique & Zéro Port de Contrôle Local :** Seul `CentralController` (`CARINA_GATEWAY_ROLE=owner`) lance `bin/carina-go`. La liaison de commande entre Python et Go s'exécute strictement via des tubes OS anonymes (`pipe(2)` NDJSON `stdin`/`stdout`), tandis que `AI_Process` et `UI` reflètent l'état à travers [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py).
- **NTCIP 1202, UTMC2 & SNMPv3 USM :** Implémente les OID canoniques NTCIP 1202 (statut `.4.1.*` / contrôle `.5.1.*`), les OID de demande/phase UTMC2, le décodage entier/chaîne d'octets `GetBitmask` (`src_go/pkg/snmp/codec.go`), SNMPv3 USM complet (`NoAuthNoPriv`, `AuthNoPriv`, `AuthPriv`), ainsi que des surcharges d'OID `config_path` par carrefour persistées dans `hardware_controller_connections.snmp_config` et dans les feuilles CSV.
- **Décodeur Binaire de Trappes SNMP & Protection Inter-Vert :** [`snmp_decoder.go`](../../src_go/pkg/traplistener/snmp_decoder.go) décode les trappes et informs binaires SNMPv1/v2c/v3, tandis que [`HardwareStageActuator`](../../src/drivers/hardware_stage_actuator.py) ignore les maintiens conflictuels durant les intervalles inter-vert jaune/tout-rouge.
- **Fail-Safe Atomique de Sécurité & Récupération :** Sur `EOF`/`SIGPIPE`, Go invoque `ShutdownAll()` via SNMP ; lors des expirations Watchdog en cours d'exécution, `EmergencyReleaseControlAll()` met en pause les pulsations et libère les maintiens tout en conservant les pilotes et l'écouteur de trappes actifs afin que `resume_control` (`ResumeControlAll()`) puisse reprendre sans reconnecter les sockets.
- **Adaptateur Transparent (`GoTrafficDriverProxy` & `RemoteHardwareDriverProxy`) :** Les proxys local et distant respectent tous deux `BaseTrafficDriver` (LSP), rendant l'orchestration matérielle transparente pour `ActionSupervisor` et `StepProcessor`.

---

## 7. Superviseur de Processus & Récupération après Crash F.E.N.I.X. (`src/fenix/`)

CARINA intègre **F.E.N.I.X.** (*Fault-tolerant Engine for Networked Intelligent eXecution*) pour garantir l'auto-guérison autonome continue 24h/24 et 7j/7 du moteur d'inférence IA :

```text
       ┌────────────────────────────────────────────────────────┐
       │            Moniteur de Santé Watchdog                  │
       └───────────────────────────┬────────────────────────────┘
                                   │ Expiration / Pulsation Manquée
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            FenixSupervisor (Orchestrateur)             │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- Recul en fenêtre glissante│ │- Cycle de vie sous-proc │
       │- Limiteur de quota restarts│ │- SIGTERM / SIGKILL      │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ Relance
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- Télémétrie FROZEN_SYNC │
                                      │- FenixStageDispatcher   │
                                      │- Bascule zéro collision │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`) & `fenix_supervision_loop.py` :** Coordonne la terminaison des sous-processus, les temporisations de récupération, la résurrection du processus enfant et la confirmation `HANDOVER_COMPLETE`.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`) :** Calcule les délais de recul exponentiels et applique des limites de taux de redémarrage pour prévenir les tempêtes de redémarrage en cascade.
- **`SubprocessRunner` (`src/fenix/process_runner.py`) :** Gestion de bas niveau des sous-processus assurant une isolation déterministe et une terminaison propre par SIGTERM/SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`) & `FenixStageDispatcher` (`src/controller/fenix_stage_dispatcher.py`) :** Maintient le moteur IA ressuscité en mode `FROZEN_SYNC`, interroge les étapes réelles des contrôleurs via `HardwareTelemetryDecoder` et ne déclenche `fenix_post_resurrection` -> `fenix_handover_complete` qu'aux frontières de phase sans collision.

---

## 8. Cycle de Vie des Agents, PBT Intra-Phase & Moteur de Promotion (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA structure les politiques d'apprentissage par renforcement comme un organisme en évolution soumis à un cursus de développement en 3 étapes :

```text
  ┌──────────────────┐    Chute Entropie & Rythme      ┌──────────────────┐   Entropie & Marge Fluides (delta*)   ┌──────────────────┐
  │   STADE ENFANT   │ ──────────────────────────────> │ STADE ADOLESCENT │ ────────────────────────────────────> │   STADE ADULTE   │
  │   (Mode Ombre)   │                                 │(Autonomie Hors-Pk│                                       │(Pleine Autonomie)│
  └────────┬─────────┘                                 └────────┬─────────┘                                       └────────┬─────────┘
           │                                                    │                                                          │
           ▼                                                    ▼                                                          ▼
  [Protégé du PBT]                                     [PBT Intra-Phase]                                          [PBT Intra-Phase]
  [Observe Dynamique Fluides]                          (ADO <-> ADO uniquement)                                   (ADULTE <-> ADULTE uniq)
  [Plancher Minimal 1 Semaine]                         [Mode Ombre en Pointes]                                    [Contrôle Actif 24/7]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`) :** Service applicatif central et façade orchestrant les évaluations de maturité des agents, appuyé par l'entité riche `AgentMaturity`, `MaturityConfig` et `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`) :** Exécute l'**Entraînement Basé sur la Population Intra-Phase**. Les agents clonent et mutent strictement au sein de leur cohorte de pairs (`TEEN` avec `TEEN`, `ADULT` avec `ADULT`), tandis que les agents `CHILD` restent totalement préservés. Intègre la vérification dimensionnelle des tenseurs pour empêcher les plantages sur des carrefours hétérogènes.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`) :** Vérifie rigoureusement l'entropie de Shannon de la politique, les durées minimales d'épisodes et les cibles de performance.
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`) :** Dimensionne dynamiquement les pas par épisode à partir de la topologie physique (unification des voies bidirectionnelles, exclusion des connecteurs internes `:` et application de la relaxation sous-linéaire $\sqrt{N}$ et $D_{\text{km}}$), calculant le plancher inviolable d'1 semaine complète ($E_{\text{semaine}}$ épisodes à $\Delta t = 250\text{ ms}$).
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`) :** Suit et persiste de façon atomique la couverture des 168 heures hebdomadaires ($7\text{ jours} \times 24\text{ heures}$), assurant la résilience aux pauses et redémarrages sans perte d'historique de maturation.
- **`ActionAuthorizer` (`src/core/action_authorizer.py`) :** Restreint le contrôle physique de l'agent `TEEN`, imposant le mode ombre pendant les heures de pointe urbaines classiques (06h30-09h00 et 17h00-19h30 les jours ouvrés) ou selon la planification de Synapse.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`) :** Orchestre le rythme dynamique en intégrant `EpisodeStepCalculator` et en imposant le plancher de sécurité inviolable ($t_{\min} = \max(E_{\text{semaine}}, \text{configuration})$).
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`) :** Calcule en continu les marges de graduation requises $\delta^* \in [3.0\%, 25.0\%]$ en exploitant la télémétrie empirique d'enfance de vitesse et d'occupation issue de `synapse_fluid_dynamics`.

---

## 9. Sous-Système d'Équilibrage Physique des Récompenses (`src/engine/reward_weights_calculator.py`)

Afin d'éliminer la distorsion du gradient lorsque les temps d'attente cumulés dépassent le débit véhiculaire de plusieurs ordres de grandeur, CARINA équilibre l'équation de récompense selon la physique de traversée de tronçons du Highway Capacity Manual (HCM) :

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`) :** Calcule les poids normalisés de récompense lors du chargement de la topologie réseau (`TopologyManager.load_topology`).
- **`RewardCalculator` (`src/engine/reward_calculator.py`) :** Intègre les poids dynamiques via `set_reward_weights`, établissant un équilibre physique où l'incitation à évacuer un véhicule correspond à l'échelle du retard accumulé en file d'attente.

---

## 10. Sous-Système de Programmation de Jaune Clignotant Nocturne (`src/controller/yellow_schedule_manager.py`)

Pour la sécurité routière et la conformité légale pendant les heures creuses nocturnes, CARINA intègre un sous-système autonome de programmation de jaune clignotant :
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`) :** Évalue les plages horaires programmées (ex. 23h00 à 05h00) par rapport à l'heure système, ordonnant de façon autonome aux contrôleurs physiques de basculer en mode jaune clignotant ou de revenir au contrôle adaptatif par IA aux frontières de plage.
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`) :** Interface IHM permettant aux opérateurs d'activer/désactiver les programmations, de personnaliser les plages horaires et d'assigner sélectivement des carrefours individuels ou des réseaux métropolitains entiers.

---

## 11. Sous-Système de Préemption pour Véhicules d'Urgence (EVP) (`src/evp/`, `src_go/evp_go/`)

Pour ouvrir des Couloirs Verts instantanés aux véhicules d'intervention d'urgence (SAMU, Pompiers, Police) conformément à la Résolution CONTRAN nº 960 et à l'Art. 29 du CTB, CARINA intègre un sous-système dédié de Préemption pour Véhicules d'Urgence :

```text
 Antenne GPS / Balise       Passerelle Web Go (:2201 / :8085)     EVPService (src/evp/)
          │                             │                                   │
          │── POST /api/v1/evp/telemetry ─>│                                   │
          │   (HTTP 204 No Content)     │── Flux NDJSON / En Mémoire ──────>│
          │                             │                                   ├── Cinématique (Haversine WGS84)
          │                             │                                   ├── Entrée de Porte (60m <= d <= 160m)
          │                             │                                   └── Vérification Sirène Active
          │                             │                                           │
          │                             │                                           ▼
          │                             │                                 SafetyAuditor (Règle #0)
          │                             │                                 (Dégagement -> ACTION_HOLD)
          │                             │                                           │
          │<───── Couloir Vert ─────────┼── SNMP ascPhaseHold (Dispatcher Go) <─────┘
```

- **Déclenchement à Double Facteur :** La préemption exige simultanément l'entrée dans la zone d'approche ($60\text{ m} \le d \le 160\text{ m}$) ET une sirène active (`siren_active = True`).
- **Interception Prioritaire par SafetyAuditor :** La Règle #0 intercepte les actions proposées, respecte les intervalles de dégagement (jaune et tout-rouge) et maintient le vert (`ACTION_HOLD = 1`).
- **Limite Watchdog CONTRAN ($45\text{ s}$) :** Interrompt inconditionnellement les maintiens après 45 secondes pour éviter le blocage transversal de la circulation.
- **Sortie Immédiate (*Checkout*) :** Dès que le véhicule franchit la ligne d'arrêt ($d \le 15\text{ m}$), la préemption est immédiatement levée.

Pour les spécifications techniques complètes, voir [Préemption pour Véhicules d'Urgence (EVP)](evp_and_preemption.md).

---

## 12. Architecture Web du Central Control Operator (CCO) & Sécurité de Transport (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA fournit un centre d'opérations basé sur le web sécurisé pour les murs d'écrans municipaux et la surveillance à distance :
- **`WebGatewayServer` (`src_go/web_gateway/server.go`, `auth.go`) :** Serveur HTTP/HTTPS Go intégré s'exécutant sur le port 2201 (`CARINA_GATEWAY_PORT`). Valeur par défaut `gateway_enabled=False` (retournant `503 Service Unavailable` jusqu'à activation), applique une authentification par jeton Bearer/en-tête en temps constant (`CARINA_CCO_AUTH_TOKEN`, `CARINA_EVP_AUTH_TOKEN`), des origines CORS explicites (`CARINA_CCO_ALLOWED_ORIGIN`), la terminaison TLS (`CARINA_GATEWAY_TLS_CERT`/`KEY`), le streaming SSE (`/cco/stream`), les points d'accès topologiques (`/cco/topology`) et le tunnel Tailscale Funnel.
- **`CCOBroadcastClient` (`src/sds/cco_broadcast_client.py`, `cco_tls_transport.py`) :** Éditeur non bloquant de type *latest-wins* transmettant les mises à jour SDS vers `/cco/broadcast` avec authentification `X-CCO-Token`, vérification CA TLS et épinglage optionnel de l'empreinte SHA-256 du certificat feuille (`PinnedHTTPSConnection`).
- **`Sécurité gRPC Synapse` (`src/communication/grpc_security.py`) :** Prend en charge TLS/mTLS (`CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_REQUIRE_CLIENT_CERT`) et `BearerTokenServerInterceptor` (`CARINA_GRPC_AUTH_TOKEN`) sur `:50051`.
- **`Application Web CCO` (`src_tsx/src_cco/`) :** Tableau de bord en React 18, TypeScript, Tailwind CSS, moteur de rendu SVG et graphiques Apache ECharts avec animations CSS uniquement sur le compositeur (`transform`/`opacity`), références de glisser-déposer de vue par `requestAnimationFrame`, différenciation de modèle de vue par égalité superficielle et mise en pause des minuteries sous `document.hidden`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
