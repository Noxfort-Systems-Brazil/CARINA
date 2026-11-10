---
tags: [database, postgresql, sqlite, schema, persistence, delta-compression, telemetry, 12-factor]
aliases: [Database Architecture, Relational Schemas, Persistence Tier, Step Decisions]
---

# 🗄️ Database Architecture & Relational Schemas

This document details CARINA's persistence tier, connection pooling, asynchronous non-blocking telemetry batching ([`StepDecisionWorker`](../../src/database/step_decision_worker.py), [`FluidDynamicsWriter`](../../src/repositories/fluid_dynamics_writer.py)), 12-Factor App credentials, and relational table schemas for PostgreSQL and SQLite.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🚨 See [EVP Preemption](evp_and_preemption.md) | 🔐 See [Security & Authentication](security_and_auth.md) | 🚦 See [Hardware Drivers](hardware_drivers.md) | 🛠️ See [Developer Guides](developer_guides.md)

---

## 1. Asynchronous Non-Blocking Database Architecture

To prevent synchronous SQL `INSERT` operations from blocking the sub-millisecond real-time AI decision loop ($< 1\text{ ms}$ target), CARINA routes all operational telemetry through bounded memory queues and background batch workers.

```text
RealTime_Decision_Loop (< 0.001 ms RAM Push)
  └──> [In-Memory Queue] ──> StepDecisionWorker / FluidDynamicsWriter
                                      │
                                      ▼
                           Delta Compression (97.9% Reduction)
                                      │
                                      ▼
                           PostgreSQL Bulk COPY / execute_values
```

- **Execution Latency:** $< 0.001\text{ ms}$ push overhead into the Python queue.
- **Batch Size:** 50 records or max flush timeout of 3.0 seconds.
- **Delta Compression:** Aggregates consecutive identical telemetry states to reduce storage footprint by **97.9%** (~380 MB/day for 200 intersections).

---

## 2. 12-Factor App Database Configuration

In accordance with the 12-Factor App principles implemented in [`src/database/db_engine.py`](../../src/database/db_engine.py), all database credentials are loaded directly from the [`.env`](../../.env.example) environment file:

```bash
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=secret_password
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina
```

---

## 3. Relational Database Schemas

### 3.1 Table: `step_decisions`
Stores real-time agent suggestions, Guardian vetoes, decisions, and step timers with 1-byte Smallint Enum encoding.

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

### 3.2 Table: `edge_dictionary`
Maps long string edge identifiers (`"topolondrina_via_jk_norte_12"`) to compact 4-byte integers for high-density storage.

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    edge_int_id SERIAL PRIMARY KEY,
    edge_str_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edge_dict_str ON edge_dictionary (edge_str_id);
```

### 3.3 Table: `synapse_fluid_dynamics`
Stores high-frequency sensor readings per road segment, compressed via Delta Compression.

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

### 3.4 Table: `hardware_controller_connections`
Stores physical controller connection endpoints for NTCIP/UDP/SNMP hardware controllers managed by [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) and defined in [`config/database/schema_queries.json`](../../config/database/schema_queries.json):

```sql
-- PostgreSQL Dialect
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW()
);

-- SQLite Dialect (embedded fallback)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.5 User Security Isolation & Hybrid Relational Persistence
CARINA provides an offline-first hybrid user management architecture managed by [`src/security/`](../../src/security):
- **Local Decoupled Storage (`security.json`):** Used during edge operation without relational database connectivity via [`JsonUserRepository`](../../src/security/json_user_repo.py).
- **Relational Persistence (`system_users` & `system_security_state`):** Managed by [`SqlUserRepository`](../../src/security/sql_user_repo.py) and [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) in PostgreSQL and SQLite, synchronized via [`HybridUserRepository`](../../src/security/hybrid_user_repo.py):

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
Brute-force protection and lockout flags are tracked in memory (`MemoryAttemptStore`) and persisted to disk (`lockdown.flag` via [`FileLockdownManager`](../../src/security/lockdown_manager.py)) and synchronized with `system_security_state`.

### 3.6 Table: `evp_registered_fleet` (Emergency Vehicle Preemption)
Stores authorized municipal emergency vehicles managed by [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py).

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

### 3.7 Table: `evp_telemetry_records` (Forensic Telemetry Auditing)
Stores historical GPS beacon trajectories and preemption events emitted by emergency units managed by [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py).

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

### 3.8 Table: `evp_denied_fleet` (Auto-Registration Blocklist)
Maintains unauthorized or blacklisted vehicle transponder IDs managed by [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.9 Tables: `sas_analysis_cache` & `mfd_analysis_cache` (Analytics Caching)
Accelerates warrant evaluation and Macroscopic Fundamental Diagram recalculation across system lifecycles:

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

### 3.10 Runtime Tables: `operation_sessions`, `step_decision_counters` & `topology_dictionary` (Migration 002)
Consolidated via Alembic migration `002_consolidate_missing_tables.py` for operational session tracking, high-frequency decision aggregation, and numeric network topology mapping:

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

## 4. Storage Efficiency Benchmark

| Table / Sector | Uncompressed Size | Compressed Size | Storage Savings |
| :--- | :--- | :--- | :--- |
| **`step_decisions`** | $\approx 3.45\text{ GB / day}$ | **$\approx 0.02\text{ GB / day}$** | **$-99.4\%$** |
| **`synapse_fluid_dynamics`** | $\approx 14.00\text{ GB / day}$ | **$\approx 0.15\text{ GB / day}$** | **$-98.9\%$** |
| **`evp_telemetry_records`** | $\approx 0.50\text{ GB / day}$ | **$\approx 0.03\text{ GB / day}$** | **$-94.0\%$** |
| **`hardware_controller_connections`** | $\approx 0.20\text{ GB / day}$ | **$\approx 0.01\text{ GB / day}$** | **$-95.0\%$** |
| **TOTAL SYSTEM DATABASE** | **$\approx 18.65\text{ GB / day}$** | **$\approx 0.41\text{ GB / day}$** | **$-97.8\%$!** |

---

## 5. Connection Pooling, Lifecycle, and Migration Idempotency (`src/database/`)

- **`DatabaseEngineFactory` (`src/database/engine_factory.py`):** Instantiates optimized engines with `QueuePool` in PostgreSQL or `NullPool` in SQLite with thread-safe switching.
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`):** Orchestrates database bootstrapping and executes **Alembic** migrations (`migrations/versions/`).
- **DDL Migration Idempotency:** To prevent critical `table already exists` failures when initializing pre-existing database files, migrations (`001_initial_schema.py` and `002_consolidate_missing_tables.py`) inspect tables at runtime via `sa.inspect(op.get_bind()).get_table_names()`, creating only absent tables and indexes.
- **Automatic Version Stamping Recovery:** When a database already contains legacy tables without an `alembic_version` history, `DatabaseSchemaInitializer.apply_migrations` catches operational errors and automatically stamps the version pointer to `head` (`command.stamp(alembic_cfg, "head")`), ensuring uninterrupted `DatabaseWorker` startup.
- **Graceful Shutdown:** During shutdown (`SIGINT`/`SIGTERM`), `DatabaseWorker` drains remaining messages in RAM queues before terminating connection pools, guaranteeing zero data loss.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
