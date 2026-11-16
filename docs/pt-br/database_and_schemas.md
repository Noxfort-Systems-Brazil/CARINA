---
tags: [database, postgresql, sqlite, schemas, delta-storage, evp, rle]
aliases: [Banco de Dados, Esquemas Relacionais, Armazenamento Delta, Modelagem SQL]
---

# 🗄️ Arquitetura de Banco de Dados, Esquemas e Armazenamento Delta

Este documento detalha a camada de persistência do CARINA localizada em [`src/database/`](../../src/database), o pipeline assíncrono de telemetria não-bloqueante via filas de RAM, a engine de compressão delta por Run-Length Encoding (RLE) no PostgreSQL e os esquemas DDL das tabelas relacionais.

⬅️ Voltar ao [Portal Central MOC](carina_moc.md) | 🏛️ Ver [Arquitetura do Sistema](architecture.md) | 🛡️ Ver [Segurança e Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempção EVP](evp_and_preemption.md)

---

## 1. Pipeline de Persistência Assíncrona Não-Bloqueante

Para evitar que latências de disco ou operações SQL `INSERT` bloqueiem o ciclo de inferência de sub-milissegundo da IA ($< 0,5\text{ ms}$), todo registro de decisão ou telemetria viária é descarregado de forma desacoplada:

```text
  Thread de Inferência (AI_Process)
                │
                ▼ (Push Não-Bloqueante em RAM < 0.001 ms)
      ┌──────────────────┐
      │   Queue db_queue │
      └─────────┬────────┘
                │
                ▼ (Consome em lotes de 50 registros ou intervalo de 3.0s)
      ┌───────────────────────────────────┐
      │          DatabaseWorker           │ (src/database/db_worker.py)
      │     (Processo de Background)      │
      └─────────────────┬─────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
  ┌──────────────┐              ┌──────────────┐
  │  PostgreSQL  │ (Produção)   │ SQLite Local │ (Desenvolvimento)
  └──────────────┘              └──────────────┘
```

### 1.1 Mecânica de Armazenamento Delta (Run-Length Encoding)
Em cruzamentos reais, os semáforos frequentemente mantêm o mesmo estágio verde por dezenas de segundos consecutivos. Em vez de gravar uma linha por segundo:
1. O worker compara o estado semafórico atual com o registro anterior.
2. Se a ação, decisão do Guardian e código de veto forem idênticos, o worker apenas incrementa a coluna `step_count` do registro ativo em memória.
3. Quando ocorre uma transição de estágio ou alteração de veto, o registro consolidado é gravado fisicamente via `INSERT`.

---

## 2. Benchmark de Redução de Armazenamento em Produção

Resultados empíricos medidos em rede urbana com 200 cruzamentos semaforizados operando 24/7 a $1\text{ Hz}$ de amostragem:

| Métrica | Ingestão Convencional (Raw) | Compressão Delta CARINA | Ganho / Redução |
| :--- | :---: | :---: | :---: |
| **Linhas gravadas por dia** | $17.280.000\text{ linhas}$ | **$362.880\text{ linhas}$** | **97,9% menos linhas** |
| **Volume de disco diário** | $\approx 18,2\text{ GB/dia}$ | **$\approx 382\text{ MB/dia}$** | **Economia de 97,9%** |
| **I/O Overhead na CPU de IA** | Bloqueante ($5\text{--}15\text{ ms}$) | **Zero ($< 0,001\text{ ms}$)** | **Totalmente desacoplado** |
| **Tempo de Consulta Forense** | Varredura de tabelas gigantescas | Índices compactos $B\text{-Tree}$ | **Aceleração de $48\times$** |

---

## 3. Esquemas DDL das Tabelas Relacionais

### 3.1 Tabela: `step_decisions`
Registra decisões de agentes táticos, auditorias do Guardian e tempos de execução com enums `SMALLINT` de 1 byte:

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
    step_count INTEGER NOT NULL DEFAULT 1,          -- Contador de Compressão Delta RLE
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_step_dec_agent_time ON step_decisions (agent_id, created_at DESC);
```

### 3.2 Tabela: `synapse_fluid_dynamics`
Armazena métricas de fluxo contínuo de tráfego (velocidade média, ocupação, extensão de filas):

```sql
CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
    id BIGSERIAL PRIMARY KEY,
    edge_id VARCHAR(64) NOT NULL,
    occupancy REAL NOT NULL,
    mean_speed_ms REAL NOT NULL,
    queue_length_m REAL NOT NULL,
    vehicle_count INT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fluid_edge_time ON synapse_fluid_dynamics (edge_id, created_at DESC);
```

### 3.3 Tabela: `hardware_controller_connections`
Catálogo de conexões com controladores físicos de tráfego e JSON opcional de SNMPv2c/v3 / sobrescrita de OIDs (`snmp_config`) gerenciado por [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) (e fachada [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py)) conforme definido em [`config/database/schema_queries.json`](../../config/database/schema_queries.json):

```sql
-- Dialeto PostgreSQL
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW(),
    snmp_config TEXT
);

-- Dialeto SQLite (contingência embarcada)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snmp_config TEXT
);
```

*(Observação: As tabelas de resumo horário `synapse_edge_phase_hourly_summary` e `synapse_intersection_phase_hourly_summary` também incluem `scenario_name` em sua chave primária composta `(..., scenario_name)` para isolamento multi-cenário, e as queries de expurgo/intervalo PostgreSQL em `config/database/fluid_dynamics_queries.json` utilizam chamadas parametrizadas `make_interval(...)`.)*

### 3.4 Tabela: `edge_dictionary`
Dicionário de mapeamento de vias urbanas para IDs numéricos compactos:

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    id SERIAL PRIMARY KEY,
    edge_str VARCHAR(128) UNIQUE NOT NULL,
    length_m REAL,
    speed_limit_kmh REAL,
    lane_count SMALLINT DEFAULT 1
);
```

### 3.5 Isolamento de Segurança de Usuários e Persistência Híbrida Relacional
O CARINA adota uma arquitetura híbrida de gerenciamento de usuários offline-first gerenciada por [`src/security/`](../../src/security):
- **Armazenamento Local Desacoplado (`security.json`):** Utilizado em operação de borda (edge) sem conectividade com banco relacional via [`JsonUserRepository`](../../src/security/json_user_repo.py).
- **Persistência Relacional (`system_users` e `system_security_state`):** Gerenciada por [`SqlUserRepository`](../../src/security/sql_user_repo.py) e [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) em PostgreSQL e SQLite, sincronizada via [`HybridUserRepository`](../../src/security/hybrid_user_repo.py):

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
A proteção contra força bruta e as flags de bloqueio são mantidas em memória (`MemoryAttemptStore`), persistidas em disco (`lockdown.flag` via [`FileLockdownManager`](../../src/security/lockdown_manager.py)) e sincronizadas com a tabela `system_security_state`.

### 3.6 Tabela: `evp_registered_fleet` (Preempção de Emergência)
Registro de viaturas autorizadas a interagir com os semáforos gerenciado por [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py):

```sql
CREATE TABLE IF NOT EXISTS evp_registered_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    corporation VARCHAR(32) NOT NULL,               -- 'SAMU', 'BOMBEIRO', 'POLICIA'
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

### 3.7 Tabela: `evp_telemetry_records` (Histórico de Trajetórias)
Rastreabilidade forense de todas as transmissões de telemetria das viaturas gerenciada por [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py):

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

### 3.8 Tabela: `evp_denied_fleet` (Bloqueio Administrativo)
Lista negra de viaturas revogadas ou com transponders defeituosos gerenciada por [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py):

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.9 Tabelas: `sas_analysis_cache` e `mfd_analysis_cache` (Cache de Análises)
Aceleram o cálculo de justificativas técnicas (warrants) e do Diagrama Fundamental Macroscópico entre reinicializações do sistema:

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

### 3.10 Tabelas de Execução: `operation_sessions`, `step_decision_counters` e `topology_dictionary` (Migration 002)
Consolidadas via migration Alembic `002_consolidate_missing_tables.py` para auditoria de sessões de operação, agregação de decisões de alto volume e mapeamento topológico da malha:

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

## 4. Configuração de Variáveis de Ambiente (`.env`)

O CARINA adota o padrão **12-Factor App**. As credenciais de banco de dados e segredos nunca são incluídos no código-fonte:

```bash
CARINA_DB_TYPE=postgresql                  # 'postgresql' ou 'sqlite'
CARINA_DB_HOST=127.0.0.1
CARINA_DB_PORT=5432
CARINA_DB_USER=carina_admin
CARINA_DB_PASSWORD=segredo_forte_aqui
CARINA_DB_NAME=carina_telemetry
CARINA_DB_POOL_SIZE=10
CARINA_DB_MAX_OVERFLOW=20
```

---

## 5. Pooling de Conexões, SQLite WAL, Ciclo de Vida & Retenção (`src/database/`)

- **`PostgresConnectionPool` & `db_transaction` ([`src/database/connection_pool.py`](../../src/database/connection_pool.py)):** Pool de conexões thread-safe para PostgreSQL construído sobre `psycopg2.pool.ThreadedConnectionPool` (`minconn=1, maxconn=16`) com `PooledPostgresConnectionProxy` e gerenciamento determinístico de commit/rollback/fechamento em `db_transaction`.
- **`configure_sqlite_connection` ([`connection_pool.py`](../../src/database/connection_pool.py)):** Aplica `PRAGMA busy_timeout = 30000`, `PRAGMA foreign_keys = ON`, `PRAGMA synchronous = NORMAL`, `PRAGMA temp_store = MEMORY` e `PRAGMA journal_mode = WAL` único para eliminar contenção de escrita entre subprocessos.
- **Modo de Worker Somente-Leitura (`enable_step_worker=False`):** Workers analíticos/de laudos (`XaiWorker`, `ReportDataCollector`, `XaiAgentRepository`) obtêm `DatabaseManager.get_instance(..., enable_step_worker=False)` sem instanciar threads `StepDecisionWorker` redundantes.
- **`DatabaseEngineFactory` (`src/database/engine_factory.py`):** Instancia engines de migração SQLAlchemy com `QueuePool` no PostgreSQL ou `NullPool` no SQLite.
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`):** Orquestra o bootstrap de tabelas e executa as migrations do **Alembic** (`migrations/versions/`).
- **Idempotência DDL & Auto-Stamping:** As migrations (`001_initial_schema.py` e `002_consolidate_missing_tables.py`) inspecionam tabelas em tempo de execução via `sa.inspect(op.get_bind()).get_table_names()` e recuperam esquemas legados sem registro de versão com `command.stamp(alembic_cfg, "head")`.
- **Expurgo Automático de Retenção (`database_worker.py`):** A consolidação horária remove registros brutos de `synapse_fluid_dynamics` com mais de 48 horas e apaga registros de `evp_telemetry_records` mais antigos que **168 horas (7 dias)**.
- **Graceful Shutdown:** No encerramento do CARINA (`SIGINT`/`SIGTERM`), o `DatabaseWorker` drena todas as mensagens remanescentes nas filas de RAM antes de encerrar os pools de conexões (`engine.close()`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
