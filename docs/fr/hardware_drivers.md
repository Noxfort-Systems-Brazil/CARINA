---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Pilotes Matériels, Contrôleurs Physiques, NTCIP 1202, Intégration UTMC]
---

# 🚦 Pilotes Matériels & Intégration des Contrôleurs Physiques

Ce document spécifie la couche d'intégration matérielle physique de CARINA située dans [`src/drivers/`](../../src/drivers) et [`src/controller/`](../../src/controller). Il détaille les protocoles de communication (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), la gestion du cycle de vie des connexions, l'acquisition de télémétrie matérielle et le basculement déterministe en mode de sécurité repli (*fail-safe*).

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🏛️ Voir [Architecture Multiprocessus](architecture.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🚑 Voir [Préemption EVP](evp_and_preemption.md)

---

## 1. Vue d'Ensemble de l'Architecture

CARINA s'interface avec les contrôleurs de feux réels (ex. Econolite, Siemens, Peek, SWARCO, Yunex) au moyen d'une **Passerelle Matérielle Go** haute performance (`bin/carina-go` compilée à partir de [`src_go/`](../../src_go)). La communication entre le cœur Python de CARINA et la passerelle Go s'effectue strictement via les **tubes standards du système d'exploitation (`stdin`/`stdout`)** au format JSON délimité par des retours à la ligne (NDJSON). Cela garantit **zéro port réseau ouvert sur la machine hôte** pour l'IPC local, une exécution sous la milliseconde et une libération totale des contraintes du GIL Python.

En plus du contrôle NTCIP/UTMC standard, la passerelle Go inclut un **Répartiteur de Préemption EVP** (`src_go/evp_go/dispatcher.go`) pour les maintiens de phase à la microseconde et une **Passerelle Web Distante** autonome (`src_go/web_gateway/server.go`) offrant une connectivité réseau maillé Tailscale, l'ingestion de télémétrie HTTP (port `2201`) et la diffusion par Server-Sent Events (SSE) pour les murs d'écrans CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │  (État & Pooling)    │   │   │ (Watchdog Pulsation) │
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
                                  │ stdin / stdout (IPC NDJSON - Zéro Port Hôte)
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
      │  │ Dispatcher EVP   │ │  GoSNMP  │ │TrapListener UDP  │   │
      │  │(Maintien Direct) │ │UDP Pt 161│ │    (Port 162)    │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestion Web Distante & Mesh
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │         Passerelle Web & Réseau Tailscale (Port 2201)     │
      │  - POST /api/v1/evp/telemetry (Ingestion GPS HTTP 204)    │
      │  - GET /cco/stream (Hub SSE Temps Réel pour Mur d'Écrans) │
      │  - Tailscale Funnel / Réseau Maillé Échiffré Poste à Poste│
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

### 2.2 Table de Correspondance des OID Standards

| Nom de l'Objet | OID ASN.1 | Type | Description |
| :--- | :--- | :---: | :--- |
| `ascPhaseStatusGroupReds` | `1.3.6.1.4.1.1206.4.2.1.1.1` | `OCTET STRING` | Masque binaire des phases actuellement au Rouge. |
| `ascPhaseStatusGroupYellows` | `1.3.6.1.4.1.1206.4.2.1.1.2` | `OCTET STRING` | Masque binaire des phases actuellement au Jaune. |
| `ascPhaseStatusGroupGreens` | `1.3.6.1.4.1.1206.4.2.1.1.3` | `OCTET STRING` | Masque binaire des phases actuellement au Vert. |
| `ascPhaseHold` | `1.3.6.1.4.1.1206.4.2.1.1.5` | `OCTET STRING` | Maintient la phase active au vert (empêche le changement de phase). |
| `ascPhaseForceOff` | `1.3.6.1.4.1.1206.4.2.1.1.6` | `OCTET STRING` | Force la fin de la phase verte en cours. |
| `ascPhaseCall` | `1.3.6.1.4.1.1206.4.2.1.1.7` | `OCTET STRING` | Injecte un appel synthétique de détection véhiculaire pour demander la phase. |

---

## 3. Pilote UTMC / UTMC2 (Norme Britannique)

Pour les carrefours utilisant le cadre britannique **Urban Traffic Management and Control (UTMC)** :

### 3.1 Architecture des Fichiers
**Implémentation dans la Passerelle Go (`src_go/`) :**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go) : Gestionnaire natif de communication UTMC en Go.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go) : Analyseur de trames de confirmation d'étape et de réponses.
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go) : Exécution des demandes d'étape et des changements d'étape.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go) : Associe les étapes UTMC (Étape 1..8) aux actions neuronales de CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) & [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json) : Définitions des profils d'OID UTMC intégrés.

---

## 4. Répartiteur Matériel de Préemption EVP (`src_go/evp_go/`)

Le **Répartiteur de Préemption EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) traite les demandes de couloirs verts d'urgence en temps réel avec un actionnement des contrôleurs physiques à la sous-milliseconde :

- **Court-Circuite le Cycle d'Inférence :** Les déclencheurs de préemption contournent la sélection standard d'actions par réseau de neurones et les cycles de coordination entre carrefours, appliquant directement des maintiens verts sur les phases de signalisation cibles.
- **Insertion de Maintien OID SNMP :** Traduit les indices d'étapes vertes en masques de bits NTCIP `ascPhaseHold` (`1.3.6.1.4.1.1206.4.2.1.1.5`), maintenant le trafic conflictuel au rouge tout en octroyant une priorité absolue et ininterrompue.
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

### 6.1 Cycle de Vie des Connexions & Pooling (`src/controller/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) : Gère les machines à états de connexion (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`).
- [`src/controller/connection_config_repo.py`](../../src/controller/connection_config_repo.py) : Persiste les adresses IP, ports, protocoles et identifiants dans la table `hardware_controller_connections`.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py) : Exécute le basculement d'urgence.

### 6.2 Déterminisme du Fail-Safe
1. **Perte de Pulsation (< 500 ms) :** Si la communication avec un contrôleur actif est interrompue pendant plus de 3 intervalles d'interrogation consécutifs, CARINA libère immédiatement tous les maintiens de phase (*Phase Holds*) et commandes de coupure forcée (*Force-Off*).
2. **Réversion Locale du Contrôleur :** Le contrôleur physique bascule immédiatement sur son plan interne local coordonné à temps fixe (*Time-of-Day* ou mode Clignotant), assurant une sécurité absolue et ininterrompue du carrefour.
3. **Interception des Conflits de Sécurité :** Toutes les actions sortantes passent par [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) avant expédition, vérifiant le temps de dégagement intermédiaire et les matrices de conflits.

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
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
