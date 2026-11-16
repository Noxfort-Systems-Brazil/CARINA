---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Руководство по тестированию, Модульное тестирование, Моки безопасности, Контроль качества]
---

# 🧪 Руководство по тестированию и валидации

CARINA управляет критически важной муниципальной инфраструктурой дорожного движения. Абсолютная надежность, детерминированное модульное тестирование, программные моки контроллеров и непрерывная валидация вето безопасности являются обязательными требованиями перед внесением любых изменений в кодовую базу.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🛡️ См. [Безопасность и Watchdog](safety_and_watchdog.md) | 🚦 См. [Драйверы оборудования](hardware_drivers.md) | 🛠️ См. [Руководства разработчика](developer_guides.md) | 🚑 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md)

---

## 1. Запуск тестового набора (`pytest`)

CARINA оснащена исчерпывающим набором тестов из **967 автоматизированных тестов Python** (верифицировано через `pytest --collect-only`: **935 модульных тестов** в 192 файлах, **18 интеграционных тестов** в 8 файлах и **14 тестов** в 4 корневых тестовых файлах) плюс **46 юнит-тестов Go** в 15 файлах `*_test.go`, гарантирующим безопасность, нулевую регрессию и детерминированное микросекундное восстановление при сбоях во всех подсистемах. Все тесты расположены в каталогах [`tests/`](../../tests) и [`src_go/`](../../src_go).

### 1.1 Запуск тестов с ограничителем памяти (`scripts/pytest_limited.sh`)
Чтобы многопроцессные фикстуры PyTorch/SLM не исчерпывали ОЗУ хоста при полных прогонах, предпочтительно использовать запускатор с лимитом ядра [`scripts/pytest_limited.sh`](../../scripts/pytest_limited.sh) совместно с [`tests/memory_guard.py`](../../tests/memory_guard.py):
```bash
# Применяет лимиты systemd cgroup v2 (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# или откатывается на ulimit -d + контроль RSS дерева процессов CARINA_PYTEST_MAX_RAM_MB:
./scripts/pytest_limited.sh tests/ -v
```
- **Детерминированный возврат ресурсов:** `tests/memory_guard.py` замеряет RSS дерева процессов, выполняет мягкий `gc.collect()` / `malloc_trim()` и очищает одиночки (`GoGatewayClient`, `HardwareConnectionManager`, `DatabaseManager`, фигуры Matplotlib) через `reclaim_test_resources()`.
- **Ограничитель реальных SLM в тестах:** Загрузка реальной GGUF LLM отключена при запуске `pytest` по умолчанию, если явно не экспортирована переменная `CARINA_ALLOW_REAL_SLM=1`.

### 1.2 Прямой запуск всех тестов и генерация отчетов о покрытии
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
HTML-отчет о покрытии сохраняется в `htmlcov/index.html`.

### 1.3 Запуск нативных модульных тестов шлюза на Go (`go test`)
Для выполнения нативных тестов на Go (46 тестовых функций, покрывающих NTCIP, UTMC, SNMPv3/codec, бинарные трапы, обнаружение, fail-safe, EVP и аутентификацию/TLS веб-шлюза):
```bash
cd src_go && go test -v -race ./...
```

---

## 2. Структура каталогов тестового набора

```text
tests/
├── conftest.py                     # Общие фикстуры pytest, временные БД и мок-окружение
├── memory_guard.py                 # Монитор RSS дерева процессов, мягкая очистка GC и освобождение одиночек
├── mock_junctions.py               # Синтетический граф топологии и определения узлов
├── benchmark.py                    # Бенчмарки производительности (пропускная способность и задержки)
├── test_*.py                       # 4 корневых набора (14 тестов: sanity, инварианты, пейсинг, недельное покрытие)
│
├── unit/                           # Изолированные модульные тесты (192 файла / 935 тестов)
│   ├── test_closed_loop_hardware_control.py # Декодирование битовых масок NTCIP/UTMC и замкнутая синхронизация фаз
│   ├── test_field_readiness_configs.py # Индивидуальные config_path, передача токенов и фазовые тайминги
│   ├── test_grpc_security.py       # Тесты TLS/mTLS и BearerTokenServerInterceptor для Synapse gRPC
│   ├── test_sds_cco_broadcast_security.py # TLS и пиннинг SHA-256 листового сертификата CCOBroadcastClient
│   ├── test_guardian_calibration_and_training.py # Обучение QR-D3QN в CHILD, калибровка F2, Noisy-OR и заморозка
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool, прагмы SQLite WAL и db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE, torch.vmap, NumPy GAE, ReplayMemory в ОЗУ
│   ├── test_phase2_db_ipc_optimizations.py # SQL make_interval, ThreadSafePipeConnection и хранение EVP
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock, VRAM pynvml, mpl_utils, кэш XAI
│   ├── test_phase4_gateway_evp_ui_optimizations.py # Пауза окна MapAnimator, пагинация AuditLog, производительность CCO
│   ├── test_pytest_memory_guard.py # Замеры RSS дерева процессов, мягкий сброс и освобождение ресурсов
│   ├── test_solid_full_audit_refactoring.py # Разделенные интерфейсы и декомпозиция координаторов по SOLID
│   ├── test_solid_gateway_and_step_refactoring.py # Тесты DIP координатора шлюза и конвейера шага
│   ├── test_evp_*.py               # 12 модулей EVP (сервис, кинематика, преемпция, автопарк, маркеры UI)
│   ├── test_local_agent.py         # Выбор действий тактическим агентом PPO и цикл обновления
│   ├── test_guardian_agent.py      # Страж безопасности D3QN и валидация порогов риска
│   ├── test_strategist_agent.py    # Координатор магистралей на базе внимания ST-GATv2 Lite
│   ├── test_pae_model.py           # Тесты Action-Conditioned iTransformer PAE и неопределенности
│   ├── test_remote_gateway_and_cco.py # Тесты веб-шлюза Tailscale и потока CCO
│   ├── test_settings_modular.py    # Модульный SettingsService, схемы, провайдеры и INI
│   ├── test_monitor_client.py      # Полиморфный MonitorClient, транспорты HTTP и MQTT
│   ├── test_go_gateway_bridge.py   # Мост IPC через пайпы к подпроцессу шлюза Go
│   ├── test_fenix_*.py             # Супервизор FENIX, раннер, политика восстановления и согласователь состояний
│   ├── security/                   # Наборы тестов криптографии, PBKDF2, политики паролей и SOLID-безопасности
│   └── ...                         # Полное покрытие модулей core, mfd, sas, xai, rendering и ui
│
└── integration/                    # Сквозные интеграционные тесты системы (8 модулей / 18 тестов)
    ├── test_system_integration.py    # Полный цикл от приема телеметрии gRPC до выдачи фазы
    ├── test_gateway_ipc_pipeline.py  # Конвейер IPC по анонимным пайпам NDJSON шлюза на Go
    ├── test_gateway_ownership_and_fenix_roundtrip.py # Владение CARINA_GATEWAY_ROLE owner/remote и цикл FENIX
    ├── test_go_gateway_snmp_hil_loopback.py # HIL-петля между реальным бинарником Go и мок-агентом SNMP
    ├── test_hft_performance_sla.py   # Валидация субмиллисекундного SLA цикла принятия решений HFT
    ├── test_postgres_migrations.py   # Миграции схем PostgreSQL Alembic и откат изменений
    ├── test_traffic_light_drivers.py # Интеграционные проверки высокоуровневых драйверов NTCIP/UTMC
    └── test_watchdog_resilience.py   # Отказоустойчивость Watchdog при таймаутах и воскрешение
```

---

## 3. Написание тестов вето безопасности (`SafetyAuditor`)

Каждое новое фазовое действие или переключение обязательно тестируется через [`src/core/safety_auditor.py`](../../src/core/safety_auditor.py):

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """Проверка наложения вето аудитором при преждевременной смене фазы до истечения минимального зеленого."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # Симуляция текущего состояния: Фаза 1 активна всего 3.0 секунды
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Попытка преждевременно переключить на Фазу 2

    # Аудит действия
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Принудительное удержание активной фазы
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """Проверка правила SR-00: активная преемпция форсирует зеленый коридор при соблюдении клиренса."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # Агент RL запросил Фазу 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Принудительный выбор целевой фазы коридора EVP
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. Мокирование драйверов аппаратных контроллеров

При запуске тестов в среде без подключенных физических контроллеров используются фикстуры моков из [`tests/conftest.py`](../../tests/conftest.py), эмулирующие сетевые ответы UDP SNMP:

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
