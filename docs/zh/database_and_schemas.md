---
tags: [database, postgresql, sqlite, schema, persistence, delta-compression, telemetry, 12-factor]
aliases: [数据库架构, 关系模式, 持久化层, 步进决策存储]
---

# 🗄️ 数据库架构与关系数据库模式

本文档详尽规范了 CARINA 的数据持久化层、数据库连接池技术、异步非阻塞遥测批量写入机制（[`StepDecisionWorker`](../../src/database/step_decision_worker.py)、[`FluidDynamicsWriter`](../../src/repositories/fluid_dynamics_writer.py)）、12-Factor 原则配置凭据管理，以及面向 PostgreSQL 与 SQLite 的规范关系型数据表模式。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🚨 查阅 [EVP 优先通行](evp_and_preemption.md) | 🔐 查阅 [安全机制与身份认证](security_and_auth.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🛠️ 查阅 [开发者指南](developer_guides.md)

---

## 1. 异步非阻塞数据库写入架构

为了彻底防止同步 SQL `INSERT` 磁盘 I/O 阻塞亚毫秒级的人工智能实时决策主循环（目标延迟 $< 1\text{ ms}$），CARINA 将所有底层运行遥测通过有界内存队列路由至后台批量处理工作进程：

```text
实时决策主循环 (< 0.001 ms RAM 快速入队)
  └──> [有界内存队列] ──> StepDecisionWorker / FluidDynamicsWriter
                                      │
                                      ▼
                           增量差分压缩 (存储减少 97.9%)
                                      │
                                      ▼
                           PostgreSQL 批量 COPY / execute_values 写入
```

- **执行延迟：** 向 Python 内存队列推送数据的开销 $< 0.001\text{ ms}$。
- **批处理规模：** 攒满 50 条记录或达到 3.0 秒最大刷写超时时钟触发落盘。
- **增量差分压缩（Delta Compression）：** 聚合连续相同的时序遥测状态，将海量时序存储占用缩减 **97.9%**（对于包含 200 个路口的都市级路网，每天全量数据仅占用约 380 MB）。

---

## 2. 12-Factor 原则数据库配置

遵循在 [`src/database/db_engine.py`](../../src/database/db_engine.py) 中贯彻的 12-Factor App 架构原则，所有数据库连接敏感凭据均直接由 [`.env`](../../.env.example) 环境变量文件加载解析：

```bash
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=secret_password
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina
```

---

## 3. 关系型数据库模式定义

### 3.1 数据表：`step_decisions`
存储实时智能体提议动作、Guardian 安全否决记录、最终执行决策以及单步执行计时器，采用 1 字节 Smallint 枚举进行极速索引与存储。

```sql
CREATE TABLE IF NOT EXISTS step_decisions (
    id BIGSERIAL PRIMARY KEY,
    simulation_time REAL NOT NULL,
    step_number INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    maturity_stage SMALLINT NOT NULL DEFAULT 2,     -- 0=CHILD 幼年, 1=TEEN 青年, 2=ADULT 成年
    suggested_action SMALLINT NOT NULL DEFAULT 0,   -- 0=KEEP 维持, 1=CHANGE 切换, 2=OVERRIDE 覆盖
    final_decision SMALLINT NOT NULL DEFAULT 0,     -- 0=APPROVED 批准, 1=DENIED 否决
    veto_reason_code SMALLINT NOT NULL DEFAULT 0,   -- 0=NONE 无, 1=MIN_GREEN 最短绿灯, 2=YELLOW 黄灯, 3=ALL_RED 全红, 4=MIN_RED 最短红灯, 5=SPILLBACK 溢流, 6=EVP_PREEMPTION 应急优先
    step_count INTEGER NOT NULL DEFAULT 1,          -- 增量差分压缩连续命中步数
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sd_agent_time ON step_decisions (agent_id, created_at DESC);
CREATE INDEX idx_sd_final_decision ON step_decisions (final_decision, veto_reason_code);
```

### 3.2 数据表：`edge_dictionary`
将冗长的路段全称字符串（如 `"topolondrina_via_jk_norte_12"`）映射为紧凑的 4 字节整数，实现高密度外键存储。

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    edge_int_id SERIAL PRIMARY KEY,
    edge_str_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edge_dict_str ON edge_dictionary (edge_str_id);
```

### 3.3 数据表：`synapse_fluid_dynamics`
存储高频微观传感器在各道路断面采集的时序流体动力学指标，采用游程增量差分算法压缩。

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

### 3.4 数据表：`hardware_controller_connections`
存储现场 NTCIP/UDP/SNMP 物理信号机硬件通信连接端点及可选的 SNMPv2c/v3 / OID 覆盖 JSON（`snmp_config`），由 [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py)（及向后兼容门面 [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py)）管理，并定义于 [`config/database/schema_queries.json`](../../config/database/schema_queries.json)：

```sql
-- PostgreSQL 方言
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW(),
    snmp_config TEXT
);

-- SQLite 方言 (嵌入式本地备用)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snmp_config TEXT
);
```

*(注：小时级汇总表 `synapse_edge_phase_hourly_summary` 与 `synapse_intersection_phase_hourly_summary` 亦将 `(..., scenario_name)` 纳入复合主键以实现多场景隔离，同时 `config/database/fluid_dynamics_queries.json` 中的 PostgreSQL 清理与时间区间查询均采用参数化 `make_interval(...)` 调用。)*

### 3.5 用户安全凭据与混合持久化 (`security.json` & SQL)
CARINA 采用由 [`src/security/`](../../src/security) 统一管理的离线优先混合用户管理架构：
- **本地解耦存储 (`security.json`)：** 在无关系型数据库连接的边缘计算节点环境下，通过 [`JsonUserRepository`](../../src/security/json_user_repo.py) 运行。
- **关系型持久化 (`system_users` 与 `system_security_state`)：** 由 [`SqlUserRepository`](../../src/security/sql_user_repo.py) 与 [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) 在 PostgreSQL 和 SQLite 中维护，并通过 [`HybridUserRepository`](../../src/security/hybrid_user_repo.py) 保持双向同步：

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
防暴力破解与账户锁定状态在内存中跟踪（`MemoryAttemptStore`），持久化至磁盘（通过 [`FileLockdownManager`](../../src/security/lockdown_manager.py) 生成 `lockdown.flag`），并同步写入 `system_security_state` 数据表。

### 3.6 数据表：`evp_registered_fleet` (特勤应急车队准入库)
存储经官方认证授权接入系统的应急特种车辆，由 [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py) 统一管理。

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

### 3.7 数据表：`evp_telemetry_records` (特勤遥测司法级取证库)
存储应急特勤车辆上报的历史高精 GPS 定位轨迹与优先控制事件记录，由 [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py) 统一管理。

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

### 3.8 数据表：`evp_denied_fleet` (未授权特勤终端黑名单)
维护未经授权或被系统拉黑的非法车载终端标识，由 [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py) 统一管理。

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.9 数据表：`sas_analysis_cache` 与 `mfd_analysis_cache` (分析计算缓存)
加速系统各生命周期阶段对工程判据（Warrants）与宏观基本图（MFD）的重复计算：

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

### 3.10 运行时数据表：`operation_sessions`, `step_decision_counters` 与 `topology_dictionary` (迁移 002)
通过 Alembic 迁移脚本 `002_consolidate_missing_tables.py` 统合，用于运营会话追踪、高频控制决策聚合统计及路网拓扑数字编码：

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

## 4. 存储效率基准测试

| 数据表 / 业务板块 | 未压缩原始体积 | 增量压缩后体积 | 存储空间缩减比 |
| :--- | :--- | :--- | :--- |
| **`step_decisions`** | $\approx 3.45\text{ GB / 天}$ | **$\approx 0.02\text{ GB / 天}$** | **$-99.4\%$** |
| **`synapse_fluid_dynamics`** | $\approx 14.00\text{ GB / 天}$ | **$\approx 0.15\text{ GB / 天}$** | **$-98.9\%$** |
| **`evp_telemetry_records`** | $\approx 0.50\text{ GB / 天}$ | **$\approx 0.03\text{ GB / 天}$** | **$-94.0\%$** |
| **`hardware_controller_connections`** | $\approx 0.20\text{ GB / 天}$ | **$\approx 0.01\text{ GB / 天}$** | **$-95.0\%$** |
| **全系统综合数据库** | **$\approx 18.65\text{ GB / 天}$** | **$\approx 0.41\text{ GB / 天}$** | **$-97.8\%$!** |

---

## 5. 连接池管理、SQLite WAL、生命周期与保留策略 (`src/database/`)

- **`PostgresConnectionPool` 与 `db_transaction` ([`src/database/connection_pool.py`](../../src/database/connection_pool.py))：** 基于 `psycopg2.pool.ThreadedConnectionPool`（`minconn=1, maxconn=16`）构建的线程安全 PostgreSQL 连接池，配合 `PooledPostgresConnectionProxy` 与确定性的 `db_transaction` 提交/回滚/归还上下文管理器。
- **`configure_sqlite_connection` ([`connection_pool.py`](../../src/database/connection_pool.py))：** 自动配置 `PRAGMA busy_timeout = 30000`、`PRAGMA foreign_keys = ON`、`PRAGMA synchronous = NORMAL`、`PRAGMA temp_store = MEMORY` 以及一次性 `PRAGMA journal_mode = WAL`，彻底消除子进程间的写锁竞争。
- **只读工作进程模式 (`enable_step_worker=False`)：** 分析与报告生成工作进程（`XaiWorker`、`ReportDataCollector`、`XaiAgentRepository`）通过 `DatabaseManager.get_instance(..., enable_step_worker=False)` 获取实例，避免派生冗余的 `StepDecisionWorker` 线程。
- **`DatabaseEngineFactory` (`src/database/engine_factory.py`)：** 实例化用于 Alembic 迁移的 SQLAlchemy 引擎（PostgreSQL 启用 `QueuePool`，SQLite 启用 `NullPool`）。
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`)：** 统筹数据模型初始化并调用 **Alembic** 执行版本迁移链 (`migrations/versions/`)。
- **迁移 DDL 严格幂等性与自动盖戳：** 迁移脚本（`001_initial_schema.py` 与 `002_consolidate_missing_tables.py`）在运行时通过 `sa.inspect(op.get_bind()).get_table_names()` 检查现有数据表，并针对未盖戳的遗留表结构通过 `command.stamp(alembic_cfg, "head")` 自动恢复版本指针。
- **自动数据保留清理 (`database_worker.py`)：** 每小时定时汇总任务自动清理超过 48 小时的原始 `synapse_fluid_dynamics` 明细，并清除超过 **168 小时（7 天）** 的 `evp_telemetry_records` 历史记录。
- **优雅停机排空 (Graceful Shutdown)：** 收到终止信号（`SIGINT`/`SIGTERM`）时，`DatabaseWorker` 优先排空内存写入队列后再关闭连接池（`engine.close()`），实现全生命周期零数据丢失。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
