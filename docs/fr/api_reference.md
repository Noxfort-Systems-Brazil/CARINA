---
tags: [api, grpc, ipc, reference, protobuf]
aliases: [Référence API, Synapse HFT, Files IPC, Interface gRPC]
---

# ⚡ Référence API & Spécifications du Protocole Synapse HFT

Ce document constitue la spécification officielle des interfaces de CARINA. Il couvre le **Protocole gRPC Synapse HFT**, les **Métriques de l'Exportateur Prometheus** ainsi que les **Schémas de Communication Inter-Processus (IPC)**.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🛡️ Voir [Sécurité & Watchdog](safety_and_watchdog.md) | 🗄️ Voir [Base de Données & Schémas](database_and_schemas.md)

---

## 1. Définition du Service gRPC Synapse HFT (`proto/synapse_hft.proto`)

CARINA s'interface avec les capteurs externes, les contrôleurs de feux physiques et les environnements de simulation microscopique (SUMO/CityFlow) via le **Protocole Synapse HFT** sur gRPC.

- **Port par Défaut :** `50051` (Configurable dans `config/settings.ini`)
- **Transport :** HTTP/2 sur TCP avec chiffrement TLS optionnel.
- **Package de Protocole :** `synapse.hft`

```protobuf
syntax = "proto3";
package synapse.hft;

service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

### 1.1 Décomposition des Méthodes RPC gRPC

#### `Ping`
- **Requête :** `Empty`
- **Réponse :** `SystemState` (renvoie l'état du serveur, l'indicateur booléen d'activité et l'horodatage époque UTC `server_time`).
- **Objectif de Latence :** $< 1\text{ ms}$

#### `LoadScenario`
- **Requête :** `ScenarioDefinition` (transfère la géométrie binaire de la carte `.net.xml.gz`, les nœuds/arêtes topologiques et le JSON d'horaires de pointe extrait par le classifieur ADAGIO).
- **Réponse :** `ScenarioStatus` (booléen `accepted` et message de statut).

#### `SystemControl`
- **Requête :** `ControlCommand` (Action d'énumération : `START`, `PAUSE`, `STOP`, `RESET`).
- **Réponse :** `CommandResponse` (booléen `success` et chaîne `new_state`).

#### `StreamTraffic`
- **Requête :** `stream TrafficFrame` (Flux haute fréquence d'occupation des tronçons, vitesses véhiculaires, longueurs de file et densités).
- **Réponse :** `SystemState`

---

## 2. Schémas des Messages de Télémétrie & de Contrôle

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // Ratio [0.0 - 1.0] of road occupancy
  float mean_speed = 2;     // Space-mean speed in m/s
  int32 queue_length = 3;   // Number of stopped vehicles in queue
  float density = 4;        // Vehicles per kilometer
}
```

### 2.2 `ScenarioDefinition`
```protobuf
message ScenarioDefinition {
  string map_hash = 1;
  TopologyGraph graph = 2;
  MapGeometry geometry = 3;
  bytes map_file_content = 4;
  string map_file_name = 5;
  string peak_schedule_json = 6;
}
```

---

## 3. Spécifications des Files de Communication Inter-Processus (IPC)

CARINA gère 10 canaux IPC bornés créés par le [`ProcessManager`](../../src/launcher/process_manager.py).

| Nom de File | Taille Max | Processus Producteur | Processus Consommateur | Schéma de Charge Utile / Type de Message |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Tube | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Tube | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | Tous Microservices | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Métriques de trafic historiques pour agrégation PostgreSQL |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | Commandes IHM, dérogations, minutages manuels & paramètres |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | Paquets télémétriques temps réel en mémoire sans port, congestion & maturité |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `InfrastructureClient` | Rapports de mandats d'ingénierie & recommandations de minutage |
| **`mfd_trigger`** | 10 | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

Pour l'actionnement des contrôleurs physiques via NTCIP et UTMC, voir [Pilotes Matériels](hardware_drivers.md).

---

## 4. Métriques de l'Exportateur Prometheus

Le `MetricsManager` expose la télémétrie opérationnelle en temps réel sur le **port HTTP 8001** (chemin `/metrics`).

```text
# Prometheus Metric Summary:
carina_step_latency_seconds_bucket{le="0.005"}   # gRPC telemetry to actuation latency histogram
carina_ppo_reward_total                          # Cumulative reward for PPO Tactical Agent
carina_guardian_veto_total{type="symbolic"}      # Counter of symbolic safety vetoes
carina_guardian_veto_total{type="neural"}        # Counter of PAE neural spillback vetoes
carina_mfd_network_density_veh_km               # Macroscopic network density
carina_mfd_network_flow_veh_hr                   # Macroscopic network throughput
carina_active_processes_count                    # Count of alive backend microservices
```

---

## 5. Télémétrie et Protocoles d'Interrogation Monitor Externes (`src/transports/`)

CARINA transmet en temps réel les pulsations d'état et les alertes matérielles aux tableaux de bord d'opérations externes et plateformes de télémétrie cloud via [`MonitorClient`](../../src/communication/monitor_client.py) et [`src/transports/`](../../src/transports).

### 5.1 Charges Utiles de Télémétrie

#### Charge Utile d'Alerte d'Incident (`noxfort/incidents/` ou HTTP POST)
```json
{
  "intersection_id": "cruzamento_av_jk_01",
  "level": "CRITICAL",
  "category": "HARDWARE_DISCONNECT",
  "message": "[FailsafeManager] Controller dropped connection. Reverting to fixed-time.",
  "occurred_at": "2026-09-15T01:30:00Z",
  "is_active": true
}
```

#### Charge Utile de Télémétrie de Pulsation (`noxfort/telemetry/` ou HTTP POST)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

### 5.2 Protocoles de Transport

| Protocole | Exemple de Configuration (`CARINA_MQTT_HOST`) | Implémentation | Caractéristiques |
| :--- | :--- | :--- | :--- |
| **Courtier MQTT** | `127.0.0.1:1883` ou `broker.emqx.io` | [`MonitorMqttTransport`](../../src/transports/mqtt_transport.py) | Paho MQTT v2, keepalive 60s, canaux `noxfort/telemetry/` et `noxfort/incidents/`. |
| **HTTP / HTTPS REST** | `https://monitor.noxfort.com/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | JSON `POST`, session persistante `requests.Session`, repli exponentiel, timeout 3,0s. |
| **Tunnels Cloud (Ngrok)** | `https://xxxx.ngrok-free.dev/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | Détection automatique via `endpoint_resolver.py` routant via tunnel HTTPS sécurisé. |

### 5.3 Règles de Classification des Points de Terminaison
La fonction factory [`create_monitor_transport()`](../../src/transports/factory.py) résout automatiquement le transport adéquat :
1. Si la chaîne d'hôte commence par `http://` ou `https://` $\implies$ **Transport HTTP**.
2. Si la chaîne d'hôte contient `.ngrok`, `.run.app` ou un chemin `/api/` $\implies$ **Transport HTTP** (préfixe automatiquement `https://` si le schéma était omis).
3. Si la chaîne d'hôte contient une adresse IP ou un domaine avec port optionnel (ex. `10.0.0.1:1883`) $\implies$ **Transport MQTT**.

---

## 6. API HTTP d'Ingestion de Télémétrie des Véhicules d'Urgence

La passerelle web Go compilée expose une interface d'ingestion à haut débit et unidirectionnelle (sans attente de réponse) pour les balises GPS des véhicules de secours :

- **Point de Terminaison :** `POST /api/v1/evp/telemetry` (alias : `POST /amb` ou `POST /amb/`)
- **Port :** `2201` (Passerelle Web / Tailscale Funnel) ou `8085` (récepteur autonome Python)
- **Réponse :** `204 No Content` (Retour immédiat pour une exécution sous la milliseconde)
- **Schéma de la Charge Utile :**
  ```json
  {
    "vehicle_id": "SAMU-01",
    "corporation": "SAMU",
    "latitude": -23.31028,
    "longitude": -51.16278,
    "speed_kmh": 65.4,
    "heading_deg": 180.0,
    "siren_active": true,
    "timestamp": 1789458600.0
  }
  ```

---

## 7. Jeu de Commandes IPC NDJSON de la Passerelle Matérielle & Web Go

Commandes transmises du noyau Python de CARINA vers `bin/carina-go` via les tubes standards anonymes (`stdin`/`stdout`) :

| Commande (`cmd`) | Arguments / Charge Utile | Données de Réponse | Description |
| :--- | :--- | :--- | :--- |
| **`ping`** | Aucun | `"pong"` | Vérifie la vivacité de la passerelle ($< 1\text{ ms}$). |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `protocol`, `green_stages` | Métadonnées de connexion | Établit la session SNMP/UDP avec le contrôleur de terrain. |
| **`disconnect`** | `intersection_id` | `success: true` | Ferme la connexion et libère le socket. |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | Applique l'action neuronale ou de sécurité aux groupes de signaux physiques. |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `vehicle_id` | Chaîne action exécutée | Envoie les maintiens de préemption d'étape à la microseconde aux contrôleurs de terrain. |
| **`cco_broadcast`** | `data: dict` | `success: true` | Transmet les trames de télémétrie aux clients SSE CCO connectés. |
| **`tailscale_status`** | Aucun | JSON `TailscaleStatus` | Interroge le domaine Tailscale Funnel, l'état du nœud et les URL publiques CCO. |
| **`emergency_release`** | Aucun | `success: true` | Relâche inconditionnellement tous les maintiens de phase sur l'ensemble du réseau métropolitain. |

---

## 8. Points de Terminaison REST & SSE du Central Control Operator (CCO)

Disponibles sur le port `2201` de la passerelle web Go (et sécurisés via Tailscale Funnel) :

- **`GET /health`** : Renvoie le statut de santé du système et la disponibilité de la passerelle.
- **`GET /cco` & `GET /cco/`** : Sert l'interface web CCO compilée en React 18.
- **`GET /cco/stream`** : Flux persistant Server-Sent Events (SSE) diffusant les états des feux en temps réel, les cartes thermiques de congestion et les positions des véhicules d'urgence vers les murs d'écrans.
- **`GET /cco/topology`** : Fournit les géométries de tronçons GeoJSON/JSON, les correspondances de voies et les coordonnées de carrefours pour le rendu cartographique.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
