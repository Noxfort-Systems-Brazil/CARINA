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
Stocke les points de terminaison des contrôleurs physiques pour les contrôleurs NTCIP/UDP/SNMP gérés par [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) et définis dans [`config/database/schema_queries.json`](../../config/database/schema_queries.json) :

```sql
-- Dialecte PostgreSQL
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW()
);

-- Dialecte SQLite (secours embarqué)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.5 Isolation de la Sécurité des Utilisateurs et Persistance Relationnelle Hybride
CARINA fournit une architecture hybride de gestion des utilisateurs conçue pour le mode hors-ligne, administrée par [`src/security/`](../../src/security) :
- **Stockage Local Découplé (`security.json`) :** Utilisé lors des opérations en périphérie (edge) sans connectivité à une base de données relationnelle via [`JsonUserRepository`](../../src/security/json_user_repo.py).
- **Persistance Relationnelle (`system_users` & `system_security_state`) :** Gérée par [`SqlUserRepository`](../../src/security/sql_user_repo.py) et [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) sous PostgreSQL et SQLite, synchronisée via [`HybridUserRepository`](../../src/security/hybrid_user_repo.py) :

```sql
CREATE TABLE IF NOT EXISTS system_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'OPERATOR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_security_state (
    id VARCHAR(32) PRIMARY KEY,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    locked_until TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
La protection contre les attaques par force brute et les indicateurs de verrouillage sont conservés en mémoire (`MemoryAttemptStore`), enregistrés sur disque (`lockdown.flag` via [`FileLockdownManager`](../../src/security/lockdown_manager.py)) et synchronisés avec la table `system_security_state`.

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

### 3.9 Tables : `sas_analysis_cache` & `mfd_analysis_cache` (Cache Analytique)
Accélère l'évaluation des justifications techniques (warrants) et le recalcul du Diagramme Fondamental Macroscopique au cours des cycles système :

```sql
CREATE TABLE IF NOT EXISTS sas_analysis_cache (
    scenario_name VARCHAR(255) PRIMARY KEY,
    metrics_cache JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mfd_analysis_cache (
    scenario_name VARCHAR(255) NOT NULL,
    cache_type VARCHAR(50) NOT NULL,
    metrics_cache JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (scenario_name, cache_type)
);
```

### 3.10 Tables d'Exécution : `operation_sessions`, `step_decision_counters` & `topology_dictionary` (Migration 002)
Consolidées via la migration Alembic `002_consolidate_missing_tables.py` pour le suivi des sessions d'exploitation, l'agrégation de décisions à haute fréquence et la modélisation topologique numérique du réseau :

```sql
CREATE TABLE IF NOT EXISTS operation_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'EM_OPERACAO',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS step_decision_counters (
    agent_id BIGINT NOT NULL,
    decision_code INT NOT NULL,
    count BIGINT DEFAULT 0 NOT NULL,
    PRIMARY KEY (agent_id, decision_code)
);

CREATE TABLE IF NOT EXISTS topology_dictionary (
    id BIGSERIAL PRIMARY KEY,
    element_type VARCHAR(20) NOT NULL,
    raw_net_id VARCHAR(255) UNIQUE NOT NULL,
    numeric_id BIGINT NOT NULL,
    custom_name VARCHAR(255) NOT NULL,
    from_node VARCHAR(100),
    to_node VARCHAR(100),
    is_bidirectional_pair BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_topodict_raw ON topology_dictionary (raw_net_id);
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

## 5. Pool de Connexions, Cycle de Vie et Idempotence des Migrations (`src/database/`)

- **`DatabaseEngineFactory` (`src/database/engine_factory.py`) :** Instancie des moteurs optimisés avec `QueuePool` sous PostgreSQL ou `NullPool` sous SQLite avec commutation thread-safe sécurisée.
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`) :** Orchestre l'initialisation des schémas et applique les migrations gérées par **Alembic** (`migrations/versions/`).
- **Idempotence DDL des Migrations :** Pour éviter les échecs critiques du type `table already exists` au démarrage sur des bases existantes, les migrations (`001_initial_schema.py` et `002_consolidate_missing_tables.py`) inspectent dynamiquement les tables à l'exécution avec `sa.inspect(op.get_bind()).get_table_names()`, ne créant que les entités et index manquants.
- **Récupération par Marquage Automatique de Version :** Lorsqu'une base de données contient déjà des tables héritées sans historique dans `alembic_version`, `DatabaseSchemaInitializer.apply_migrations` intercepte les erreurs opérationnelles et synchronise automatiquement le pointeur de révision sur `head` (`command.stamp(alembic_cfg, "head")`), garantissant un démarrage propre du `DatabaseWorker`.
- **Arrêt Propre (Graceful Shutdown) :** Lors de l'arrêt du processus (`SIGINT`/`SIGTERM`), le `DatabaseWorker` vide les files d'attente en mémoire RAM avant de fermer les connexions, garantissant zéro perte de données.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingénierie de Mobilité Intelligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Sous licence AGPLv3 ou ultérieure (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
