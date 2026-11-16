---
tags: [database, postgresql, sqlite, schema, persistence, delta-compression, telemetry, 12-factor]
aliases: [Архитектура БД, Реляционные схемы, Уровень хранения, Решения шага]
---

# 🗄️ Архитектура базы данных и реляционные схемы

Данный документ подробно описывает уровень персистентности CARINA, организацию пулов соединений, асинхронную неблокирующую пакетную запись телеметрии ([`StepDecisionWorker`](../../src/database/step_decision_worker.py), [`FluidDynamicsWriter`](../../src/repositories/fluid_dynamics_writer.py)), конфигурацию учетных данных по принципам 12-Factor App и реляционные схемы таблиц для PostgreSQL и SQLite.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🚨 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md) | 🔐 См. [Безопасность и аутентификация](security_and_auth.md) | 🚦 См. [Драйверы оборудования](hardware_drivers.md) | 🛠️ См. [Руководства разработчика](developer_guides.md)

---

## 1. Асинхронная неблокирующая архитектура базы данных

Для предотвращения блокировки субмиллисекундного цикла принятия решений ИИ ($< 1\text{ мс}$) синхронными операциями SQL `INSERT`, CARINA направляет всю оперативную телеметрию через буферизованные очереди оперативной памяти и фоновые пакетные воркеры.

```text
Цикл принятия решений реального времени (< 0.001 мс запись в ОЗУ)
  └──> [Очередь в памяти] ──> StepDecisionWorker / FluidDynamicsWriter
                                      │
                                      ▼
                            RLE Дельта-сжатие (Сокращение объема на 97.9%)
                                      │
                                      ▼
                            Массовая вставка PostgreSQL Bulk COPY / execute_values
```

- **Задержка постановки в очередь:** Накладные расходы на отправку в очередь Python составляют $< 0.001\text{ мс}$.
- **Размер пакета (Batch Size):** 50 записей или сброс по таймауту 3.0 секунды.
- **Дельта-сжатие:** Агрегирует последовательные идентичные состояния телеметрии, сокращая дисковое пространство на **97.9%** (~380 МБ/сутки для сети из 200 перекрёстков).

---

## 2. Конфигурация базы данных по стандарту 12-Factor App

В соответствии с принципами методологии 12-Factor App, реализованными в [`src/database/db_engine.py`](../../src/database/db_engine.py), все параметры подключения к БД загружаются напрямую из файла переменных окружения [`.env`](../../.env.example):

```bash
CARINA_DB_USER=admin
CARINA_DB_PASSWORD=secret_password
CARINA_DB_HOST=localhost
CARINA_DB_PORT=5432
CARINA_DB_NAME=carina_data
CARINA_DB_SCHEMA=schema_carina
```

---

## 3. Реляционные схемы базы данных

### 3.1 Таблица: `step_decisions`
Хранит предложения агентов реального времени, вето Guardian, принятые решения и таймеры тактов с компактным 1-байтовым кодированием перечислений Smallint Enum.

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
    step_count INTEGER NOT NULL DEFAULT 1,          -- Количество последовательных тактов при дельта-сжатии
    total_step_time_ms REAL,
    guardian_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sd_agent_time ON step_decisions (agent_id, created_at DESC);
CREATE INDEX idx_sd_final_decision ON step_decisions (final_decision, veto_reason_code);
```

### 3.2 Таблица: `edge_dictionary`
Сопоставляет длинные строковые идентификаторы ребер графа сети (`"topolondrina_via_jk_norte_12"`) компактным 4-байтовым целым числам для сверхплотного хранения.

```sql
CREATE TABLE IF NOT EXISTS edge_dictionary (
    edge_int_id SERIAL PRIMARY KEY,
    edge_str_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edge_dict_str ON edge_dictionary (edge_str_id);
```

### 3.3 Таблица: `synapse_fluid_dynamics`
Хранит высокочастотные показания детекторов по дорожным сегментам, сжатые с помощью алгоритма Delta Compression.

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

### 3.4 Таблица: `hardware_controller_connections`
Хранит конечные точки сетевых подключений физических дорожных контроллеров и опциональный JSON переопределений SNMPv2c/v3 / OID (`snmp_config`) под управлением [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) (и фасада [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py)) в соответствии с [`config/database/schema_queries.json`](../../config/database/schema_queries.json):

```sql
-- Диалект PostgreSQL
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP DEFAULT NOW(),
    snmp_config TEXT
);

-- Диалект SQLite (встроенный резерв)
CREATE TABLE IF NOT EXISTS hardware_controller_connections (
    intersection_id TEXT PRIMARY KEY,
    ip_address TEXT NOT NULL,
    auto_connect BOOLEAN NOT NULL DEFAULT 1,
    last_connected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    snmp_config TEXT
);
```

*(Примечание: таблицы почасовых сводок `synapse_edge_phase_hourly_summary` и `synapse_intersection_phase_hourly_summary` также включают `scenario_name` в составной первичный ключ `(..., scenario_name)` для изоляции сценариев, а запросы очистки/интервалов PostgreSQL в `config/database/fluid_dynamics_queries.json` используют параметризованные вызовы `make_interval(...)`.)*

### 3.5 Безопасность пользователей и гибридное хранилище (`security.json` и SQL)
CARINA использует гибридную архитектуру управления пользователями с приоритетом локальной работы (offline-first), реализованную в модуле [`src/security/`](../../src/security):
- **Локальное изолированное хранилище (`security.json`):** Используется при автономной работе на периферийных узлах (edge) без постоянного подключения к СУБД через [`JsonUserRepository`](../../src/security/json_user_repo.py).
- **Реляционное хранилище (`system_users` и `system_security_state`):** Управляется [`SqlUserRepository`](../../src/security/sql_user_repo.py) и [`SqlSecurityStateRepository`](../../src/security/sql_security_state_repo.py) в PostgreSQL и SQLite, синхронизируясь через [`HybridUserRepository`](../../src/security/hybrid_user_repo.py):

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
Защита от перебора паролей и флаги блокировки отслеживаются в оперативной памяти (`MemoryAttemptStore`), сохраняются на диск (`lockdown.flag` через [`FileLockdownManager`](../../src/security/lockdown_manager.py)) и синхронизируются с таблицей `system_security_state`.

### 3.6 Таблица: `evp_registered_fleet` (Приоритет спецтранспорта)
Хранит список авторизованных автомобилей экстренных служб под управлением [`src/evp/evp_fleet_repository.py`](../../src/evp/evp_fleet_repository.py).

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

### 3.7 Таблица: `evp_telemetry_records` (Судебный аудит телеметрии)
Хранит историю GPS-треков и события приоритетного пропуска, переданные оперативными машинами, под управлением [`src/evp/evp_telemetry_repository.py`](../../src/evp/evp_telemetry_repository.py).

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

### 3.8 Таблица: `evp_denied_fleet` (Черный список авторегистрации)
Содержит идентификаторы неавторизованных или заблокированных маяков спецтранспорта под управлением [`src/evp/evp_denied_repository.py`](../../src/evp/evp_denied_repository.py).

```sql
CREATE TABLE IF NOT EXISTS evp_denied_fleet (
    vehicle_id VARCHAR(64) PRIMARY KEY,
    denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.9 Таблицы: `sas_analysis_cache` и `mfd_analysis_cache` (Кэш аналитики)
Ускоряют расчет транспортных критериев (warrants) и макроскопической фундаментальной диаграммы (MFD) между перезапусками системы:

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

### 3.10 Таблицы времени выполнения: `operation_sessions`, `step_decision_counters` и `topology_dictionary` (Миграция 002)
Консолидированы миграцией Alembic `002_consolidate_missing_tables.py` для отслеживания рабочих сессий, высокочастотной агрегации управляющих решений и числовой топологии транспортной сети:

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

## 4. Сравнительный бенчмарк эффективности хранения

| Таблица / Сектор | Размер без сжатия | Размер со сжатием | Экономия хранилища |
| :--- | :--- | :--- | :--- |
| **`step_decisions`** | $\approx 3.45\text{ ГБ / сутки}$ | **$\approx 0.02\text{ ГБ / сутки}$** | **$-99.4\%$** |
| **`synapse_fluid_dynamics`** | $\approx 14.00\text{ ГБ / сутки}$ | **$\approx 0.15\text{ ГБ / сутки}$** | **$-98.9\%$** |
| **`evp_telemetry_records`** | $\approx 0.50\text{ ГБ / сутки}$ | **$\approx 0.03\text{ ГБ / сутки}$** | **$-94.0\%$** |
| **`hardware_controller_connections`** | $\approx 0.20\text{ ГБ / сутки}$ | **$\approx 0.01\text{ ГБ / сутки}$** | **$-95.0\%$** |
| **ОБЩАЯ БАЗА ДАННЫХ СИСТЕМЫ** | **$\approx 18.65\text{ ГБ / сутки}$** | **$\approx 0.41\text{ ГБ / сутки}$** | **$-97.8\%$!** |

---

## 5. Пул соединений, SQLite WAL, жизненный цикл и очистка данных (`src/database/`)

- **`PostgresConnectionPool` и `db_transaction` ([`src/database/connection_pool.py`](../../src/database/connection_pool.py)):** Потокобезопасный пул соединений PostgreSQL поверх `psycopg2.pool.ThreadedConnectionPool` (`minconn=1, maxconn=16`) с `PooledPostgresConnectionProxy` и детерминированным управлением фиксацией/откатом/закрытием транзакций `db_transaction`.
- **`configure_sqlite_connection` ([`connection_pool.py`](../../src/database/connection_pool.py)):** Применяет `PRAGMA busy_timeout = 30000`, `PRAGMA foreign_keys = ON`, `PRAGMA synchronous = NORMAL`, `PRAGMA temp_store = MEMORY` и однократный `PRAGMA journal_mode = WAL` для устранения конкуренции при записи между подпроцессами.
- **Режим воркеров только на чтение (`enable_step_worker=False`):** Аналитические и отчетные воркеры (`XaiWorker`, `ReportDataCollector`, `XaiAgentRepository`) получают `DatabaseManager.get_instance(..., enable_step_worker=False)`, не запуская лишние фоновые потоки `StepDecisionWorker`.
- **`DatabaseEngineFactory` (`src/database/engine_factory.py`):** Создает движки SQLAlchemy для миграций с `QueuePool` для PostgreSQL или `NullPool` для SQLite.
- **`DatabaseSchemaInitializer` (`src/database/schema_initializer.py`):** Управляет инициализацией схемы и запуском миграций под управлением **Alembic** (`migrations/versions/`).
- **Идемпотентность DDL в миграциях и автомаркировка:** Миграции (`001_initial_schema.py` и `002_consolidate_missing_tables.py`) инспектируют таблицы во время выполнения через `sa.inspect(op.get_bind()).get_table_names()` и восстанавливают унаследованные схемы без метки ревизии через `command.stamp(alembic_cfg, "head")`.
- **Автоматическая очистка по сроку хранения (`database_worker.py`):** Почасовая консолидация удаляет сырые записи `synapse_fluid_dynamics` старше 48 часов и очищает записи `evp_telemetry_records` старше **168 часов (7 дней)**.
- **Корректное завершение работы (Graceful Shutdown):** При завершении процесса (`SIGINT`/`SIGTERM`) `DatabaseWorker` полностью сбрасывает очереди из оперативной памяти на диск перед закрытием пулов соединений (`engine.close()`), исключая потерю данных.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
