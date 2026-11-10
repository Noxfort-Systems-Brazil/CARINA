---
tags: [database, postgresql, sqlite, schema, persistence, delta-compression, telemetry, 12-factor]
aliases: [Architecture Base de Données, Schémas Relationnels, Niveau de Persistance, Décisions par Pas]
---

# 🗄️ Architecture de Base de Données & Schémas Relationnels

Ce document détaille le niveau de persistance de CARINA, le regroupement de connexions en pool, le traitement par lots asynchrone non-bloquant de la télémétrie ([`StepDecisionWorker`](../../src/database/step_decision_worker.py), [`FluidDynamicsWriter`](../../src/repositories/fluid_dynamics_writer.py)), les identifiants 12-Factor App et les schémas de tables relationnelles pour PostgreSQL et SQLite.

⬅️ Retour au [Hub Principal de Documentation](carina_moc.md) | 🚨 Voir [Préemption EVP](evp_and_preemption.md) | 🔐 Voir [Sécurité & Authentification](security_and_auth.md) | 🚦 Voir [Pilotes Matériels](hardware_drivers.md) | 🛠️ Voir [Guides du Développeur](developer_guides.md)

---

## 1. Architecture de Base de Données Asynchrone Non-Bloquante

Afin d'éviter que les opérations synchrones SQL `INSERT` ne bloquent la boucle de décision de l'IA en temps réel sous la milliseconde (objectif $< 1\text{ ms}$), CARINA achemine toute la télémétrie opérationnelle via des files de mémoire bornées et des processus de traitement par lots en arrière-plan.

```text
Boucle_Décision_Temps_Réel (< 0.001 ms RAM Push)
  └──> [File en Mémoire] ──> StepDecisionWorker / FluidDynamicsWriter
                                      │
                                      ▼
                           Compression Delta (97.9% de Réduction)
                                      │
                                      ▼
                           PostgreSQL Bulk COPY / execute_values
```

- **Latence d'Exécution :** Surcoût d'insertion $< 0.001\text{ ms}$ dans la file d'attente Python.
- **Taille de Lot :** 50 enregistrements ou délai d'évacuation maximal de 3,0 secondes.
- **Compression Delta :** Agrège les états de télémétrie consécutifs identiques pour réduire l'empreinte de stockage de **97.9%** (~380 Mo/jour pour 200 carrefours).

---

## 2. Configuration de Base de Données 12-Factor App

Conformément aux principes 12-Factor App implémentés dans [`src/database/db_engine.py`](../../src/database/db_engine.py), tous les identifiants de base de données sont chargés directement depuis le fichier d'environnement [`.env`](../../.env.example) :

```bash
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=secret_password
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina
```

---

## 3. Schémas de Base de Données Relationnelle

### 3.1 Table : `step_decisions`
Stocke les suggestions des agents en temps réel, les vetos de Guardian, les décisions finales et les durées d'étape avec encodage d'énumération Smallint sur 1 octet.

```sql
CREATE TABLE IF NOT EXISTS step_decisions (
    id BIGSERIAL PRIMARY KEY,
    simulation_time REAL NOT NULL,
    step_number INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    maturity_stage SMALLINT NOT NULL DEFAULT 2,     -- 0=CHILD, 1=TEEN, 2=ADULT
    suggested_action SMALLINT NOT NULL DEFAULT 0,   -- 0=KEEP, 1=CHANGE, 2=OVERRIDE
    final_decision SMALLINT NOT NULL DEFAULT 0,     -- 0=APPROVED, 1=DENIED (VETOED)
    veto_reason_code SMALLINT NOT NULL DEFAULT 0,   -- 0=NONE, 1=MIN_GREEN, 2=YELLOW, 3=SPILLBACK, 4=GRIDLOCK
    step_count INTEGER NOT NULL DEFAULT 1,          -- Delta Compression Consecutive Count
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sd_agent_time ON step_decisions (agent_id, created_at DESC);
CREATE INDEX idx_sd_final_decision ON step_decisions (final_decision, veto_reason_code);
```

### 3.2 Table : `edge_dictionary`
Mappe les identifiants de tronçons longs sous forme de chaîne (`"topolondrina_via_jk_norte_12"`) vers des entiers compacts sur 4 octets pour un stockage à haute densité.

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    edge_int_id SERIAL PRIMARY KEY,
    edge_str_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edge_dict_str ON edge_dictionary (edge_str_id);
```

### 3.3 Table : `synapse_fluid_dynamics`
Stocke les relevés de capteurs haute fréquence par segment de voie, compressés via la Compression Delta.

```sql
CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
    id SERIAL PRIMARY KEY,
    collected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    scenario_name TEXT NOT NULL DEFAULT 'default',
    intersection_id TEXT,
    edge_id TEXT NOT NULL,
    edge_int_id INTEGER,
    density REAL NOT NULL,
    mean_speed REAL NOT NULL,
    min_speed REAL,
    queue_length INTEGER NOT NULL,
    max_queue INTEGER,
    occupancy REAL NOT NULL,
    edge_length REAL,
    num_lanes INTEGER,
    speed_limit REAL,
    maturity_stage TEXT NOT NULL DEFAULT 'CHILD',
    sample_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_sfd_collected_at ON synapse_fluid_dynamics (collected_at);
CREATE INDEX idx_sfd_edge_id ON synapse_fluid_dynamics (edge_id);
CREATE INDEX idx_sfd_scen_stage_time ON synapse_fluid_dynamics (scenario_name, maturity_stage, collected_at DESC);
```

### 3.4 Table : `hardware_controller_connections`
Stocke les spécifications de connexion des contrôleurs physiques (points de terminaison NTCIP/UTMC).

```sql
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    id SERIAL PRIMARY KEY,
    intersection_id VARCHAR(64) UNIQUE NOT NULL,
    protocol VARCHAR(32) NOT NULL,                  -- 'NTCIP_1202', 'UTMC', 'SNMP'
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER NOT NULL DEFAULT 161,
    snmp_community VARCHAR(64) DEFAULT 'public',
    timeout_seconds REAL DEFAULT 1.0,
    retry_count INTEGER DEFAULT 3,
    status VARCHAR(32) DEFAULT 'DISCONNECTED',
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.5 Table : `users` (Niveau de Sécurité)
Stocke les comptes opérateurs et les identifiants hachés gérés par [`src/utils/security/user_repository.py`](../../src/utils/security/user_repository.py).

```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'OPERATOR',   -- 'ADMIN', 'ENGINEER', 'OPERATOR'
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.6 Table : `evp_registered_fleet` (Préemption pour Véhicules d'Urgence)
Stocke les véhicules d'urgence municipaux autorisés gérés par [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_registered_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    corporation VARCHAR(32) NOT NULL,              -- 'SAMU', 'BOMBEIRO', 'POLICIA'
    plate VARCHAR(16),
    description VARCHAR(128),
    device_id VARCHAR(64),
    ip_address VARCHAR(45),
    port INT DEFAULT 8085,
    protocol VARCHAR(16) DEFAULT 'HTTP',
    auth_token VARCHAR(128),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.7 Table : `evp_telemetry_records` (Audit Médico-Légal de la Télémétrie)
Stocke les trajectoires historiques des balises GPS et les événements de préemption émis par les unités d'urgence, gérés par [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_telemetry_records (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id VARCHAR(64) NOT NULL,
    corporation VARCHAR(32) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    speed_kmh REAL NOT NULL,
    heading_deg REAL NOT NULL,
    siren_active BOOLEAN NOT NULL,
    evp_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    intersection_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evp_veh_time ON evp_telemetry_records (vehicle_id, created_at DESC);
```

### 3.8 Table : `evp_denied_fleet` (Liste de Blocage d'Auto-Enregistrement)
Maintient les identifiants de transpondeurs de véhicules non autorisés ou sur liste noire gérés par [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Banc d'Essai d'Efficacité du Stockage

| Table / Secteur | Taille Non Compressée | Taille Compressée | Économie de Stockage |
| :--- | :--- | :--- | :--- |
| **`step_decisions`** | $\approx 3.45\text{ Go / jour}$ | **$\approx 0.02\text{ Go / jour}$** | **$-99.4\%$** |
| **`synapse_fluid_dynamics`** | $\approx 14.00\text{ Go / jour}$ | **$\approx 0.15\text{ Go / jour}$** | **$-98.9\%$** |
| **`evp_telemetry_records`** | $\approx 0.50\text{ Go / jour}$ | **$\approx 0.03\text{ Go / jour}$** | **$-94.0\%$** |
| **`hardware_controller_connections`** | $\approx 0.20\text{ Go / jour}$ | **$\approx 0.01\text{ Go / jour}$** | **$-95.0\%$** |
| **BASE DE DONNÉES SYSTÈME TOTALE** | **$\approx 18.65\text{ Go / jour}$** | **$\approx 0.41\text{ Go / jour}$** | **$-97.8\%$ !** |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3.</small>
</div>
