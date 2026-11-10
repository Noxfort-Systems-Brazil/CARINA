---
tags: [architecture, core, system, gatv2, pae, pbt, amp, multiprocessing]
aliases: [Architecture Système, Schéma Multiprocessus, Vue d'Ensemble du Système]
---

# 🏛️ CARINA : Schéma Directeur du Système & Architecture Multiprocessus

Ce document spécifie l'architecture d'ingénierie interne de l'écosystème CARINA. Il détaille les 8 microservices concurrents du système d'exploitation, la topologie canonique des réseaux neuronaux profonds (LocalAgent PPO-TCN, GuardianAgent D3QN et StrategistAgent ST-GATv2 Lite), le `TopologicalScaler`, les pilotes de contrôleurs physiques et le moteur asynchrone de stockage delta sous PostgreSQL.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🧠 Voir [Formulations Neuronales](research_notes.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md)

---

## 1. Modèle de Concurrence des Microservices Multiprocessus

Le Verrou Global de l'Interpréteur Python (GIL) empêche l'inférence IA multi-thread dépendante du processeur et les opérations d'E/S lourdes de s'exécuter en véritable parallélisme. Pour atteindre une latence d'actionnement inférieure à la milliseconde, CARINA utilise un **modèle de microservices multiprocessus** orchestré par [`carina.py`](../../carina.py) et [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py), combiné à une **Passerelle Matérielle & Web Go** de qualité industrielle (`bin/carina-go`) :

```mermaid
graph TD
    Launcher[carina.py Orchestrateur / Tray IHM] -->|Génère & Surveille| PM[ProcessManager]

    PM --> CC[1. Processus CentralController]
    PM --> AI[2. Moteur AI_Process]
    PM --> WD[3. Processus Watchdog]
    PM --> SDS[4. DashboardService SDS]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Moteur MFD_Worker]

    CC <-->|Tube IPC| AI
    AI -->|File g_state| WD
    AI -->|File db| DB
    CC -->|File sds| SDS
    CC -->|File sas| SAS
    CC -->|File mfd_trigger| MFD
    MFD -->|File mfd_results| CC
    SAS -->|File sas_results| CC
    XAI -->|Journaux Disque HFT| AI

    CC <-->|Stdin/Stdout NDJSON| GW[Passerelle Go carina-go]
    GW --> NTCIP[Contrôleurs Terrain NTCIP / UTMC UDP 161]
    GW --> WebGW[Passerelle Web Go Port 2201 / Tailscale]
    WebGW --> CCO[Carte Web CCO React/TSX src_tsx]
    WebGW <--|Télémétrie POST 204| EVP[Antennes GPS EVP Port 8085]
```

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

### 2.1 Module ST-GATv2 Lite (`src/models/st_gatv2_lite.py`)
- **Finalité :** Synchronisation spatiale des « Ondes Vertes » artérielles sur les carrefours voisins du graphe de réseau routier urbain.
- **Pondération Dynamique :** Alors que la topologie physique du réseau est statique, les coefficients dynamiques d'attention spatiale $\alpha_{ij}(t)$ sont recalculés en temps réel d'après les densités véhiculaires entrantes et les gradients de vitesse.
- **Coordination Décentralisée :** Le Strategist calcule périodiquement le tenseur de contexte spatio-temporel sur le réseau et l'injecte aux agents Local et Guardian, permettant l'émergence d'ondes vertes sans point de défaillance unique centralisé.

### 2.2 Auto-Encodeur Prédictif Universel (`src/models/pae.py`)
- **Finalité :** Moteur physique partagé à haute capacité compressant la dynamique séquentielle multi-pas en espaces latents invariants ($Z \in \mathbb{R}^{16\dots 128}$).
- **Enrichissement Ciblé :** Fournit des représentations d'état latent prédictives et compactes pour enrichir à la fois les décisions de politique du LocalAgent et l'audit de remontée de file du GuardianAgent.

### 2.3 Auto-Mise à l'Échelle Topologique en $O(1)$ (`src/utils/topo_scaler.py`)
- **Mise à l'Échelle Algorithmique :** Détecte automatiquement la densité du réseau ($N$ carrefours) et ajuste de manière autonome les dimensions neuronales en puissances de 2 optimisées pour les TensorCores NVIDIA :
  - $N \le 20 \implies \text{dim} = 32, \text{têtes} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{têtes} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{têtes} = 8$ (ex. Grille Métropolitaine de Londrina)
  - $N > 250 \implies \text{dim} = 256, \text{têtes} = 16$ (Grille Mégalopole)

### 2.4 Accélération Universelle AMP & TensorCore
- Toutes les passes avant des réseaux neuronaux sont enveloppées dans `torch.amp.autocast`, activant l'accélération matérielle native FP16/TF32 sur les TensorCores NVIDIA et limitant la consommation totale de VRAM à seulement **~20 Mo** pour les modèles centraux.

---

## 3. Données Persistantes & Moteur de Stockage Delta

CARINA implémente un moteur de persistance asynchrone utilisant la **Compression Delta par Plages** (*Run-Length Delta Compression*) sous PostgreSQL :
- **`step_decisions`** : Enregistre les suggestions, les vetos de sécurité Guardian et les durées d'étape expédiés via [`StepDecisionWorker`](../../src/database/step_decision_worker.py) dans des files de mémoire non-bloquantes (surcoût $< 0.001\text{ ms}$).
- **`edge_dictionary`** : Mappe les noms de voies longs sur des entiers de 4 octets pour un indexage compact.
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

- **`SettingsSchema` (`src/settings/schema.py`) :** Registre faisant autorité pour mapper clés-sections, valeurs de repli par défaut et validation des types.
- **`IniFileStorage` (`src/settings/ini_storage.py`) :** Gère la lecture et l'écriture persistante dans `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`) :** Résout les secrets sensibles d'infrastructure depuis `.env` via `python-dotenv` avec analyse de fichier de secours.
- **`SettingsService` (`src/settings/service.py`) :** Service central orchestrant la récupération, validation et sérialisation de la configuration.
- **`SettingsManager` (`src/utils/settings_manager.py`) :** Façade rétrocompatible garantissant zéro régression pour le code appelant existant.

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
- **Zéro Port Ouvert sur l'Hôte :** La liaison de commande entre Python et Go s'exécute exclusivement via des tubes anonymes standards (tampons circulaires du noyau `pipe(2)`). Aucun port localhost, socket ou service HTTP n'est exposé.
- **Fail-Safe Atomique de Sécurité :** Si le processus IA Python plante ou se ferme, le noyau ferme le tube. Le binaire Go détecte `EOF` sur `os.Stdin` en quelques microsecondes et déclenche immédiatement `EmergencyReleaseControlAll()` via SNMP, libérant en toute sécurité les maintiens distants et restituant le contrôle aux plans autonomes locaux des contrôleurs.
- **Zéro Contention du GIL :** Les goroutines gèrent l'interrogation concurrente, les pulsations de maintien de vie à 2,0s et la réception des trappes UDP 162 indépendamment des lourdes opérations de tenseurs PyTorch en Python.
- **Adaptateur Transparent (`GoTrafficDriverProxy`) :** Respecte le principe de substitution de Liskov (LSP) en implémentant `BaseTrafficDriver`, rendant la passerelle Go 100% transparente pour le reste de la base de code CARINA.

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
                                      │- Poignée de main limite │
                                      │- Bascule zéro collision │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`) :** Coordonne la terminaison des sous-processus, les temporisations de récupération, la résurrection du processus enfant et la réconciliation d'état.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`) :** Calcule les délais de recul exponentiels et applique des limites de taux de redémarrage pour prévenir les tempêtes de redémarrage en cascade.
- **`SubprocessRunner` (`src/fenix/process_runner.py`) :** Gestion de bas niveau des sous-processus assurant une isolation déterministe et une terminaison propre par SIGTERM/SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`) :** Garantit que le moteur IA ressuscité fonctionne en mode `FROZEN_SYNC` et n'assume le contrôle d'actionnement qu'aux frontières d'étapes sûres lors de la transition naturelle des contrôleurs physiques.

---

## 8. Cycle de Vie des Agents, PBT Intra-Phase & Moteur de Promotion (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA structure les politiques d'apprentissage par renforcement comme un organisme en évolution soumis à un cursus de développement en 3 étapes :

```text
  ┌──────────────────┐   Chute Entropie & Rythme    ┌──────────────────┐  Entropie & Marge Fluides (delta*)  ┌──────────────────┐
  │   STADE ENFANT   │ ───────────────────────────> │  STADE ADOLESCENT│ ─────────────────────────────────>  │   STADE ADULTE   │
  │   (Mode Ombre)   │                              │(Autonomie Nuit)  │                                     │(Pleine Autonomie)│
  └────────┬─────────┘                              └────────┬─────────┘                                     └────────┬─────────┘
           │                                                 │                                                        │
           ▼                                                 ▼                                                        ▼
  [Protégé du PBT]                                  [PBT Intra-Phase]                                        [PBT Intra-Phase]
  [Observe Dynamique Fluides]                       (ADO <-> ADO uniquement)                                 (ADULTE <-> ADULTE uniq)
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`) :** Service applicatif central et façade orchestrant les évaluations de maturité des agents, appuyé par l'entité riche `AgentMaturity`, `MaturityConfig` et `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`) :** Exécute l'**Entraînement Basé sur la Population Intra-Phase**. Les agents clonent et mutent strictement au sein de leur cohorte de pairs (`TEEN` avec `TEEN`, `ADULT` avec `ADULT`), tandis que les agents `CHILD` restent totalement préservés. Intègre la vérification dimensionnelle des tenseurs pour empêcher les plantages sur des carrefours hétérogènes.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`) :** Vérifie rigoureusement l'entropie de Shannon de la politique, les durées minimales d'épisodes et les cibles de performance.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`) :** Établit automatiquement le rythme des durées d'épisodes requises selon le nombre de tronçons routiers et les pas de mise à jour du réseau.
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

## 12. Architecture Web du Central Control Operator (CCO) (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA fournit un centre d'opérations basé sur le web pour les murs d'écrans municipaux et la surveillance à distance :
- **`WebGatewayServer` (`src_go/web_gateway/server.go`) :** Serveur HTTP Go intégré s'exécutant sur le port 2201 (ou port configuré) fournissant le streaming d'événements SSE (`/cco/stream`), les points d'accès topologiques (`/cco/topology`) et le tunnel distant chiffré Tailscale Funnel.
- **`Application Web CCO` (`src_tsx/src_cco/`) :** Tableau de bord moderne en React 18, TypeScript, Tailwind CSS, moteur de rendu SVG et graphiques Apache ECharts affichant en temps réel les positions des véhicules, les minutages des feux et les alertes de préemption.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
