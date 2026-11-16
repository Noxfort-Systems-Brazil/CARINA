---
tags: [base-de-datos, postgresql, sqlite, esquemas, persistencia, delta-compression, telemetria, 12-factor]
aliases: [Arquitectura de Base de Datos, Esquemas Relacionales, Nivel de Persistencia, Decisiones de Paso]
---

# 🗄️ Arquitectura de Base de Datos y Esquemas Relacionales

Este documento detalla la capa de persistencia de CARINA, el pool de conexiones, el procesamiento por lotes asíncrono no bloqueante ([`StepDecisionWorker`](../../src/database/step_decision_worker.py), [`FluidDynamicsWriter`](../../src/repositories/fluid_dynamics_writer.py)), credenciales bajo 12-Factor App y los esquemas de tablas para PostgreSQL y SQLite.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🚨 Ver [Prioridad EVP](evp_and_preemption.md) | 🔐 Ver [Seguridad y Autenticación](security_and_auth.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🛠️ Ver [Guías de Desarrollo](developer_guides.md)

---

## 1. Arquitectura Asíncrona No Bloqueante

Para evitar que las operaciones síncronas de `INSERT` en SQL bloqueen el ciclo de decisión de IA en tiempo real ($< 1\text{ ms}$), CARINA enruta toda la telemetría operativa a través de colas de memoria acotadas y trabajadores en segundo plano.

```text
Ciclo_Decision_Tiempo_Real (< 0.001 ms Push en RAM)
  └──> [Cola en Memoria] ──> StepDecisionWorker / FluidDynamicsWriter
                                      │
                                      ▼
                           Compresión Delta (97.9% Reducción)
                                      │
                                      ▼
                           PostgreSQL Bulk COPY / execute_values
```

- **Latencia de Ejecución:** Sobrecarga $< 0.001\text{ ms}$ al enviar datos a la cola Python.
- **Tamaño de Lote:** 50 registros o tiempo máximo de descarga de 3.0 segundos.
- **Compresión Delta:** Agrupa estados de telemetría consecutivos idénticos reduciendo el almacenamiento en un **97.9%** (~380 MB/día para 200 intersecciones).

---

## 2. Configuración de Base de Datos 12-Factor App

Conforme a los principios 12-Factor implementados en [`src/database/db_engine.py`](../../src/database/db_engine.py), todas las credenciales de la base de datos se cargan directamente desde el archivo de entorno [`.env`](../../.env.example):

```bash
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=secret_password
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina
```

---

## 3. Esquemas de Base de Datos Relacional

### 3.1 Tabla: `step_decisions`
Almacena sugerencias en tiempo real de los agentes, vetos del Guardian, decisiones y temporizadores de paso codificados con tipos Smallint Enum de 1 byte.

```sql
CREATE TABLE IF NOT EXISTS step_decisions (
    id BIGSERIAL PRIMARY KEY,
    simulation_time REAL NOT NULL,
    step_number INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    maturity_stage SMALLINT NOT NULL DEFAULT 2,     -- 0=CHILD, 1=TEEN, 2=ADULT
    suggested_action SMALLINT NOT NULL DEFAULT 0,   -- 0=KEEP, 1=CHANGE, 2=OVERRIDE
    final_decision SMALLINT NOT NULL DEFAULT 0,     -- 0=APPROVED, 1=DENIED (VETOED)
    veto_reason_code SMALLINT NOT NULL DEFAULT 0,   -- 0=NONE, 1=MIN_GREEN, 2=YELLOW, 3=ALL_RED, 4=MIN_RED, 5=SPILLBACK, 6=EVP_PREEMPTION
    step_count INTEGER NOT NULL DEFAULT 1,          -- Conteo Consecutivo de Compresión Delta
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sd_agent_time ON step_decisions (agent_id, created_at DESC);
CREATE INDEX idx_sd_final_decision ON step_decisions (final_decision, veto_reason_code);
```

### 3.2 Tabla: `edge_dictionary`
Mapea identificadores de vía de texto extenso (`"topolondrina_via_jk_norte_12"`) a enteros compactos de 4 bytes para almacenamiento denso.

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    edge_int_id SERIAL PRIMARY KEY,
    edge_str_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edge_dict_str ON edge_dictionary (edge_str_id);
```

### 3.3 Tabla: `synapse_fluid_dynamics`
Almacena lecturas de alta frecuencia de sensores por segmento vial, comprimidas mediante Compresión Delta.

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

### 3.4 Tabla: `hardware_controller_connections`
Almacena los endpoints de conexión a controladores físicos y el JSON opcional de SNMPv2c/v3 / anulaciones de OID (`snmp_config`) gestionados por [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) (y la fachada [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py)) según se define en [`config/database/schema_queries.json`](../../config/database/schema_queries.json):

```sql
-- Dialecto PostgreSQL
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW(),
    snmp_config TEXT
);

-- Dialecto SQLite (reserva embebida)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snmp_config TEXT
);
```

*(Nota: Las tablas de resumen horario `synapse_edge_phase_hourly_summary` y `synapse_intersection_phase_hourly_summary` también indexan su clave primaria compuesta en `(..., scenario_name)` para el aislamiento multiescenario, y las consultas de purga e intervalos en PostgreSQL de `config/database/fluid_dynamics_queries.json` utilizan llamadas parametrizadas a `make_interval(...)`.)*

### 3.5 Seguridad de Usuarios y Persistencia Híbrida (`security.json` y SQL)
CARINA implementa una arquitectura híbrida offline-first para la gestión de usuarios gestionada por [`src/security/`](../../src/security):
- **Almacenamiento Local Desacoplado (`security.json`):** Empleado en despliegues perimetrales (edge) sin conexión a base de datos relacional mediante [`JsonUserRepository`](../../src/security/json_user_repo.py).
- **Persistencia Relacional (`system_users` y `system_security_state`):** Gestionada por [`SqlUserRepository`](../../src/security/sql_user_repo.py) y [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) en PostgreSQL y SQLite, sincronizada mediante [`HybridUserRepository`](../../src/security/hybrid_user_repo.py):

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
La protección contra fuerza bruta y las banderas de bloqueo se rastrean en memoria (`MemoryAttemptStore`), se persisten en disco (`lockdown.flag` mediante [`FileLockdownManager`](../../src/security/lockdown_manager.py)) y se sincronizan con la tabla `system_security_state`.

### 3.6 Tabla: `evp_registered_fleet` (Preempción de Vehículos de Emergencia)
Almacena vehículos municipales de emergencia autorizados gestionados por [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py).

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

### 3.7 Tabla: `evp_telemetry_records` (Auditoría Forense de Telemetría)
Almacena trayectorias GPS históricas y eventos de preempción emitidos por unidades de emergencia mediante [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py).

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

### 3.8 Tabla: `evp_denied_fleet` (Lista de Bloqueo de Auto-Registro)
Mantiene transpondedores no autorizados o revocados gestionados por [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.9 Tablas: `sas_analysis_cache` y `mfd_analysis_cache` (Caché de Analítica)
Aceleran la evaluación de justificaciones técnicas (warrants) y el recalculo del Diagrama Fundamental Macroscópico entre ciclos de ejecución:

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

### 3.10 Tablas de Ejecución: `operation_sessions`, `step_decision_counters` y `topology_dictionary` (Migración 002)
Consolidadas mediante la migración Alembic `002_consolidate_missing_tables.py` para seguimiento de sesiones operativas, agregación de decisiones de alta frecuencia y mapeo topológico numérico de la red:

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

## 4. Eficiencia de Almacenamiento

| Tabla / Sector | Tamaño sin Comprimir | Tamaño Comprimido | Reducción de Almacenamiento |
| :--- | :--- | :--- | :--- |
| **`step_decisions`** | $\approx 3.45\text{ GB / día}$ | **$\approx 0.02\text{ GB / día}$** | **$-99.4\%$** |
| **`synapse_fluid_dynamics`** | $\approx 14.00\text{ GB / día}$ | **$\approx 0.15\text{ GB / día}$** | **$-98.9\%$** |
| **`evp_telemetry_records`** | $\approx 0.50\text{ GB / día}$ | **$\approx 0.03\text{ GB / día}$** | **$-94.0\%$** |
| **`hardware_controller_connections`** | $\approx 0.20\text{ GB / día}$ | **$\approx 0.01\text{ GB / día}$** | **$-95.0\%$** |
| **TOTAL BASE DE DATOS** | **$\approx 18.65\text{ GB / día}$** | **$\approx 0.41\text{ GB / día}$** | **$-97.8\%$!** |

---

## 5. Agrupamiento de Conexiones, SQLite WAL, Ciclo de Vida y Retención (`src/database/`)

- **`PostgresConnectionPool` y `db_transaction` ([`src/database/connection_pool.py`](../../src/database/connection_pool.py)):** Agrupamiento de conexiones PostgreSQL seguro para hilos construido sobre `psycopg2.pool.ThreadedConnectionPool` (`minconn=1, maxconn=16`) con `PooledPostgresConnectionProxy` y gestión determinista de commit/rollback/cierre mediante `db_transaction`.
- **`configure_sqlite_connection` ([`connection_pool.py`](../../src/database/connection_pool.py)):** Aplica `PRAGMA busy_timeout = 30000`, `PRAGMA foreign_keys = ON`, `PRAGMA synchronous = NORMAL`, `PRAGMA temp_store = MEMORY` y un ajuste único `PRAGMA journal_mode = WAL` para eliminar la contención de escritura entre subprocesos.
- **Modo Worker de Solo Lectura (`enable_step_worker=False`):** Los workers analíticos y de informes (`XaiWorker`, `ReportDataCollector`, `XaiAgentRepository`) adquieren `DatabaseManager.get_instance(..., enable_step_worker=False)` sin iniciar hilos `StepDecisionWorker` redundantes.
- **`DatabaseEngineFactory` (`src/database/engine_factory.py`):** Instancia motores de migración SQLAlchemy con `QueuePool` en PostgreSQL o `NullPool` en SQLite.
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`):** Orquesta el arranque de esquemas y ejecuta las migraciones gestionadas por **Alembic** (`migrations/versions/`).
- **Idempotencia DDL en Migraciones y Marcado Automático:** Las migraciones (`001_initial_schema.py` y `002_consolidate_missing_tables.py`) inspeccionan tablas en tiempo de ejecución mediante `sa.inspect(op.get_bind()).get_table_names()` y recuperan esquemas legados sin sello de versión mediante `command.stamp(alembic_cfg, "head")`.
- **Purga Automatizada de Retención (`database_worker.py`):** La consolidación horaria purga `synapse_fluid_dynamics` en bruto con más de 48 horas y elimina `evp_telemetry_records` con más de **168 horas (7 días)**.
- **Cierre Ordenado (Graceful Shutdown):** Durante el apagado (`SIGINT`/`SIGTERM`), el `DatabaseWorker` drena las colas de memoria RAM antes de cerrar los pools de conexiones (`engine.close()`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
