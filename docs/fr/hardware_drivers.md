---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Pilotes Matériels, Contrôleurs Physiques, NTCIP 1202, Intégration UTMC]
---

# 🚦 Pilotes Matériels & Intégration des Contrôleurs Physiques

Ce document spécifie la couche d'intégration matérielle physique de CARINA située dans [`src/drivers/`](../../src/drivers) et [`src/controller/`](../../src/controller). Il détaille les protocoles de communication (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), la gestion du cycle de vie des connexions, l'acquisition de télémétrie matérielle et le basculement déterministe en mode de sécurité repli (*fail-safe*).

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🏛️ Voir [Architecture Multiprocessus](architecture.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Vue d'Ensemble de l'Architecture

CARINA s'interface avec les contrôleurs de feux réels (ex. Econolite, Siemens, Peek, SWARCO, Yunex) au moyen d'une **Passerelle Matérielle Go** haute performance (`bin/carina-go` compilée à partir de [`src_go/`](../../src_go)). La communication entre le cœur Python de CARINA et la passerelle Go s'effectue strictement via les **tubes standards du système d'exploitation (`stdin`/`stdout`)** au format JSON délimité par des retours à la ligne (NDJSON). Cela garantit **zéro port IPC local ouvert sur la machine hôte**, une exécution sous la milliseconde et une libération totale des contraintes du GIL Python.

### 1.1 Propriétaire Unique de la Passerelle (`CARINA_GATEWAY_ROLE`) & Architecture en Boucle Fermée
Pour éviter les processus `bin/carina-go` en double, les collisions d'écoute de trappes sur le port UDP `162` et la désynchronisation d'état SNMP (*split-brain*) :
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`) :** Lance exclusivement `bin/carina-go`, héberge [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (composé de `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` et `TailscaleGatewayAdapter`), détient les connexions SNMP locales de `HardwareConnectionManager` et diffuse les instantanés vers les workers en aval.
- **`AI_Process`, `SDS` et `UI` (`CARINA_GATEWAY_ROLE=remote`) :** Opèrent comme miroirs distants sans lancer de binaire Go local ni lier le port UDP `162`. [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py) (matérialisé par [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py)) transmet les actions (`ai_hardware_cmd`) et préemptions EVP (`ai_evp_preempt`) à `CentralController` à travers [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Décodage de Télémétrie en Boucle Fermée :** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) et [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) traduisent les masques de bits des contrôleurs réels (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) en indices d'étape SUMO à base 0 pour l'extraction d'état de l'IA et la réconciliation de bascule F.E.N.I.X.

En plus du contrôle NTCIP/UTMC standard, la passerelle Go inclut un **Répartiteur de Préemption EVP** (`src_go/evp_go/dispatcher.go`) pour les maintiens de phase à la microseconde et une **Passerelle Web Distante** (`src_go/web_gateway/server.go`) offrant une connectivité réseau maillé Tailscale authentifiée par jeton, la terminaison TLS, l'ingestion de télémétrie HTTP (port `2201`) et la diffusion par Server-Sent Events (SSE) pour les murs d'écrans CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │      CentralController (CARINA_GATEWAY_ROLE=owner)     │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │  (État & SNMPv2/v3)  │   │   │ (Watchdog Pulsation) │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │(Dispatch Préemption) │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │(Sous-proc Tube Python)  │
                     └────────────┬────────────┘
                                  │ stdin / stdout (IPC NDJSON - Zéro Port de Contrôle Local)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │          PASSERELLE MATÉRIELLE CARINA (Binaire Go)        │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │    Pilote NTCIP    │         │    Pilote UTMC     │   │
      │   │ (NTCIP 1202 v02)   │         │ (UTMC2 Norme UK)   │   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │ Dispatcher EVP   │ │GoSNMPv2/3│ │Déc. Trappes Bin. │   │
      │  │(Maintien Direct) │ │UDP Pt 161│ │ (SNMPv1/v2c/v3)  │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestion Web Distante & Mesh
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │     Passerelle Web & Réseau Tailscale (Port 2201 / TLS)   │
      │  - Fail-closed par défaut (HTTP 503 si désactivée)        │
      │  - POST /api/v1/evp/telemetry (Auth Jeton, HTTP 204)      │
      │  - GET /cco/stream (Auth Jeton, CORS, Mur d'Écrans SSE)   │
      │  - Tailscale Funnel / Réseau Maillé Chiffré Poste à Poste │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. Pilote de Contrôleur de Feux NTCIP 1202 (ASC)

La **norme NTCIP 1202** (*National Transportation Communications for ITS Protocol*) est la norme dominante en Amérique du Nord et dans les déploiements ITS modernes à travers le monde.

### 2.1 Architecture des Fichiers
**Implémentation dans la Passerelle Go (`src_go/`) :**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go) : Orchestrateur natif du pilote NTCIP en Go.
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go) : Scruteur de télémétrie pour les phases actives, l'état des anneaux et les déclenchements de détecteurs.
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go) : Moteur de maintien de phase, coupure forcée (*force-off*) et injection d'appels de phase.
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go) : Traduit les actions discrètes de CARINA en masques de bits de phase NTCIP.
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) & [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json) : Définitions des profils OID intégrés.

**Pont Python & Couche Proxy (`src/drivers/`) :**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py) : Client IPC par tube anonyme NDJSON gérant le sous-processus `bin/carina-go`.
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py) : Proxy compatible `BaseTrafficDriver` transmettant les commandes au démon Go.
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py) : Instancie les proxys de pilotes selon la détection automatique de marque/modèle.

### 2.2 Table de Correspondance des OID Standards (`src_go/configs/ntcip_oids.json`)

Tous les OID NTCIP 1202 de statut (`phaseStatusGroup`) et de contrôle (`phaseControlGroup`) prennent en charge les PDU entiers et `OCTET STRING`/`BitString` via [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go), et peuvent être surchargés par carrefour via `config_path` :

| Clé d'Objet | OID ASN.1 | Groupe / Type | Description |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | Statut / Masque | Masque binaire des phases actuellement au Rouge. |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | Statut / Masque | Masque binaire des phases actuellement au Jaune. |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | Statut / Masque | Masque binaire des phases actuellement au Vert. |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | Statut / Masque | Appels actifs de détection véhiculaire signalés par le contrôleur. |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | Statut / Masque | Appels actifs de boutons-poussoirs piétons signalés par le contrôleur. |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | Contrôle / Masque | Omet certaines phases du service. |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | Contrôle / Masque | Maintient la phase active au vert (`ascPhaseControlHold`). |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | Contrôle / Masque | Force la fin de la phase verte en cours (`ascPhaseControlForceOff`). |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | Contrôle / Masque | Injecte un appel synthétique de détection véhiculaire (`ascPhaseControlVehCall`). |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | Contrôle / Masque | Injecte un appel synthétique piéton (`ascPhaseControlPedCall`). |

---

## 3. Pilote UTMC / UTMC2 & Prise en Charge SNMPv3 USM

Pour les carrefours utilisant le cadre britannique **Urban Traffic Management and Control (UTMC)** ou des armoires terrain authentifiées **SNMPv3** :

### 3.1 Architecture des Fichiers
**Implémentation dans la Passerelle Go (`src_go/`) :**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go) : Gestionnaire natif de communication UTMC en Go avec `Probe()` et `CloseTransport()` thread-safe.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go) : Analyseur de confirmation d'étape (`status_active`, `status_leaving`, `status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`, `status_ped_demand`).
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go) : Exécution de demande d'étape, maintien, coupure forcée (*force-off*) et actions logiques sûres vis-à-vis de l'inter-vert.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go) : Associe les étapes UTMC (Étape 1..8) aux actions neuronales de CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) & [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json) : Définitions des profils d'OID UTMC intégrés.
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go) : **Moteur SNMPv3 USM** prenant en charge `NoAuthNoPriv`, `AuthNoPriv` et `AuthPriv` avec protocoles d'authentification (`MD5`, `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512`) et chiffrement de confidentialité (`DES`, `AES`, `AES192`, `AES256`, `AES192C`, `AES256C`). Les métadonnées JSON `snmp_config` par carrefour et les surcharges d'OID `config_path` se propagent depuis [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) et [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) via [`DriverFactory`](../../src/drivers/driver_factory.py) jusqu'à `GoGatewayClient`.

---

## 4. Répartiteur Matériel de Préemption EVP (`src_go/evp_go/`)

Le **Répartiteur de Préemption EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) traite les demandes de couloirs verts d'urgence en temps réel avec un actionnement des contrôleurs physiques à la sous-milliseconde :

- **Court-Circuite le Cycle d'Inférence :** Les déclencheurs de préemption contournent la sélection standard d'actions par réseau de neurones et les cycles de coordination entre carrefours, appliquant directement des maintiens verts sur les phases de signalisation cibles.
- **Insertion de Maintien OID SNMP :** Traduit les indices d'étapes vertes (`stage_idx` et `stage_codes`) en masques de bits NTCIP `phase_control.hold` (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) ou en masques de maintien d'étape UTMC, maintenant le trafic conflictuel au rouge tout en octroyant une priorité absolue et ininterrompue.
- **Protocole IPC à la Microseconde :** Activé via la commande NDJSON `evp_preempt` sur les tubes de l'OS :
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **Watchdog Fail-Safe & Relâchement de Maintien :** Les maintiens sont libérés soit lorsque le véhicule franchit le seuil de sortie ($\le 15\text{ m}$), soit à l'expiration du minuteur watchdog de maintien maximal ($45\text{ s}$). Si la passerelle plante ou se déconnecte, les contrôleurs physiques relâchent automatiquement les maintiens après 3 pulsations manquées.

---

## 5. Passerelle Web Distante & Réseau Maillé (`src_go/web_gateway/`)

Pour les architectures distribuées de villes intelligentes où les véhicules d'urgence ou les opérateurs centraux ont besoin d'une connectivité distante sans exposition d'IP publique :

- **Réseau Maillé Chiffré Tailscale :** Intégré via [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go), permettant aux contrôleurs périphériques CARINA de former des réseaux superposés zéro-trust sécurisés et chiffrés de bout en bout.
- **Tailscale Funnel (Port 2201) :** Expose publiquement des points d'ingestion à haut débit via TLS sans ouvrir de ports sur le pare-feu local ni configurer de redirection de port.
- **Récepteur de Télémétrie à Haut Débit :** Expose `POST /api/v1/evp/telemetry` (HTTP 204 en mode transmission directe) pour ingérer les balises GPS de véhicules haute fréquence avec une latence de réponse inférieure à la milliseconde.
- **Hub de Diffusion Server-Sent Events (SSE) :** [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) diffuse la télémétrie des carrefours en temps réel, les trajectoires des véhicules d'urgence et les états des feux vers les murs d'écrans du Central Control Operator (CCO) via `GET /cco/stream`.

---

## 6. Gestion du Matériel & Architecture Fail-Safe

### 6.1 Cycle de Vie des Connexions & Pooling (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) & [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py) : Gèrent les machines à états de connexion (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`), les vues miroirs passives en mode `remote` (`update_remote_hardware_status`), l'autodétection des ports de simulateur ([`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)) et la restauration CSV en lot ([`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)).
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) & [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py) : Persistent les points de terminaison IP et le JSON optionnel `snmp_config` (SNMPv3 USM / `config_path` d'OID personnalisé) dans `hardware_controller_connections` et les modèles CSV, tout en préservant [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) comme façade rétrocompatible.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py) : Exécute le basculement d'urgence via `HardwareGatewayCoordinator.on_failsafe_triggered()` et la reprise via `on_failsafe_recovered()`.

### 6.2 Déterminisme du Fail-Safe, Récupération & Trappes SNMP Binaires
1. **Perte de Pulsation & Fail-Safe Réversible :** Si la communication avec un contrôleur actif est interrompue ou si le fail-safe Watchdog se déclenche, `EmergencyReleaseControlAll()` met en pause les pulsations et relâche les maintiens de phase tout en maintenant actifs les pilotes SNMP et l'écouteur de trappes afin que `resume_control` (`ResumeControlAll()`) puisse reprendre sans à-coup lors du rétablissement. À la sortie du processus ou sur `EOF`/`SIGPIPE`, `ShutdownAll()` relâche définitivement les maintiens et ferme les sockets.
2. **Protection Inter-Vert (`HardwareStageActuator`) :** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) ignore les appels `send_stage_hold` conflictuels durant les intervalles inter-vert jaune/tout-rouge (`_is_intergreen_stage`) et résout uniformément les identifiants préfixés par `tl_`.
3. **Décodeur Binaire de Trappes SNMPv1/v2c/v3 (`src_go/pkg/traplistener/snmp_decoder.go`) :** Analyse les paquets binaires ASN.1 BER Trap/Inform sur le port UDP `162` (`CARINA_TRAP_PORT`), classant les alarmes `coldStart`, `warmStart`, `linkDown`, `linkUp`, `authenticationFailure`, NTCIP (`.1206.*`) et UTMC (`.13267.*`, `.2825.*`) par gravité (`CRITICAL`, `WARNING`, `INFO`).
4. **Interception des Conflits de Sécurité :** Toutes les actions sortantes passent par [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) avant expédition, vérifiant le temps de dégagement intermédiaire et les matrices de conflits.

### 6.3 Signalement des Incidents Matériels & Déduplication (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py) : Intercepte les changements d'état matériel du contrôleur (`CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`) et construit des messages d'incident JSON standardisés.
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py) : Prévient les tempêtes de notifications en mettant en cache les empreintes d'incidents actifs avec un filtrage anti-rebond temporel dans `.carina_incident_filter_cache.json`.
- Expédie les alertes dynamiquement via `MonitorClient` vers le transport de télémétrie configuré (courtier MQTT local ou point d'accès distant HTTP/Ngrok).

---

## 7. Sécurité & Identifiants Réseau

Les identifiants matériels ne doivent jamais être codés en dur. CARINA résout les secrets SNMP et de contrôleurs via les variables d'environnement définies dans [`.env`](../../.env.example) :

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

Pour les configurations de sécurité et les rôles utilisateurs, voir [Sécurité & Authentification](security_and_auth.md).
Pour les schémas de sérialisation de télémétrie, voir la [Référence API](api_reference.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
