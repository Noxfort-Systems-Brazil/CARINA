---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Руководство по тестированию, Модульное тестирование, Моки безопасности, Контроль качества]
---

# 🧪 Руководство по тестированию и валидации

CARINA управляет критически важной муниципальной инфраструктурой дорожного движения. Абсолютная надежность, детерминированное модульное тестирование, программные моки контроллеров и непрерывная валидация вето безопасности являются обязательными требованиями перед внесением любых изменений в кодовую базу.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🛡️ См. [Безопасность и Watchdog](safety_and_watchdog.md) | 🚦 См. [Драйверы оборудования](hardware_drivers.md) | 🛠️ См. [Руководства разработчика](developer_guides.md) | 🚑 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md)

---

## 1. Запуск тестового набора (`pytest`)

CARINA оснащена исчерпывающим набором тестов из **861 автоматизированных тестов** (верифицировано через `pytest --collect-only`), гарантирующим безопасность, нулевую регрессию и детерминированное микросекундное восстановление при сбоях во всех подсистемах. Все тесты расположены в каталоге [`tests/`](../../tests).

### 1.1 Запуск всех тестов
```bash
pytest tests/ -v
```

### 1.2 Генерация отчетов о покрытии кода тестами
Для измерения покрытия ветвлений и операторов в каталоге `src/`:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
HTML-отчет о покрытии сохраняется в `htmlcov/index.html`.

### 1.3 Запуск нативных модульных тестов шлюза на Go (`go test`)
Для выполнения тестов на Go, покрывающих протоколы NTCIP, UTMC, обработку SNMP-трапов и обнаружение:
```bash
cd src_go && go test -v ./...
```

---

## 2. Структура каталогов тестового набора

```text
tests/
├── conftest.py                     # Общие фикстуры pytest, временные БД и мок-окружение
├── mock_junctions.py               # Синтетический граф топологии и определения узлов
├── benchmark.py                    # Бенчмарки производительности (пропускная способность и задержки)
│
├── unit/                           # Изолированные модульные тесты (всего 861 тестов)
│   ├── test_evp_service.py         # Жизненный цикл EVPService, конвейер приема и триггеры преемпции
│   ├── test_evp_kinematics.py      # Расчет расстояния по гаверсинусам, скорости, курса и ворот приближения
│   ├── test_evp_preemption_engine.py # Арбитраж удержания фазы, 45-секундный таймер watchdog и клиренс
│   ├── test_evp_map_topology.py    # Сопоставление с топологией, входящие подходы и фазовые соответствия
│   ├── test_evp_fleet_persistence.py # CRUD-операции авторизованного автопарка и кэширование номеров
│   ├── test_evp_config_repo.py     # Репозиторий конфигурации EVP и персистентность порогов
│   ├── test_evp_fleet_controller.py # Бизнес-логика управления флотом спецмашин и валидация
│   ├── test_evp_fleet_csv.py       # Экспорт и массовый импорт реестра автопарка из CSV
│   ├── test_evp_fleet_save_flow.py # Сквозное сохранение формы флота в UI и коммит в БД
│   ├── test_evp_hardware_parity_persistence.py # Паритет аппаратного состояния между движками БД
│   ├── test_evp_settings_handler.py # Сохранение настроек EVP в settings.ini и .env
│   ├── test_evp_vehicle_marker.py  # Отрисовка маркеров спецмашин на холсте Flet и стробоскопы
│   ├── test_local_agent.py         # Выбор действий тактическим агентом PPO и цикл обновления
│   ├── test_guardian_agent.py      # Страж безопасности D3QN и валидация порогов риска
│   ├── test_strategist_agent.py    # Координатор магистралей на базе внимания ST-GATv2 Lite
│   ├── test_settings_modular.py    # Модульный SettingsService, схемы, провайдеры и INI
│   ├── test_settings_view.py       # Экран настроек Flet Settings View и персистентность UI
│   ├── test_monitor_client.py      # Полиморфный MonitorClient, транспорты HTTP и MQTT
│   ├── test_monitor_disconnect.py  # Сценарии повторных попыток, сброса буфера и отключения
│   ├── test_core_components.py     # Тесты DecisionCoordinator и ActionAuthorizer
│   ├── test_go_gateway_bridge.py   # Мост IPC через пайпы к подпроцессу шлюза Go
│   ├── test_traffic_light_driver.py # Высокоуровневая абстракция драйвера светофорного объекта
│   ├── test_traffic_modular_components.py # Модульные компоненты дорожного регулирования
│   ├── test_driver_factory_brand_model.py # Создание экземпляров драйверов (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # Слушатели SNMP-трапов и разбор кодов ошибок
│   ├── test_connection_db_persistence.py  # Персистентность сетевых эндпоинтов контроллеров
│   ├── test_connection_manager_orchestrator.py # Оркестрация конечных автоматов соединений
│   ├── test_fenix_supervisor.py    # Жизненный цикл супервизора FENIX, восстановление и воскрешение
│   ├── test_fenix_process_runner.py # Контроль подпроцессов runner (SIGTERM/SIGKILL)
│   ├── test_fenix_recovery_policy.py # Политика скользящего окна восстановления и экспоненциальный бэкофф
│   ├── test_fenix_state_reconciler.py # Передача управления на чистой границе и синхронизация FROZEN_SYNC
│   ├── test_watchdog_fenix_integration.py # Срабатывание таймаута Watchdog и запуск воскрешения FENIX
│   ├── test_security_modular.py    # AuthService, UserService, PBKDF2 и Lockdown
│   ├── test_security_manager.py    # Валидация фасада обратной совместимости SecurityManager
│   ├── test_captum_analyzer.py     # Тесты атрибуции градиентов Integrated Gradients
│   ├── test_xai_report_builder.py  # Генерация отчетов Word по ABNT с формулами OMML
│   ├── test_multi_agent_modular_builder.py # Сборка многоагентных аналитических блоков отчета
│   ├── test_mfd_processor.py       # Базовый процессор макроскопической фундаментальной диаграммы
│   ├── test_mfd_report_generator.py # Генерация отчетов MFD и аппроксимация кривых
│   ├── test_mfd_db_reconstruction.py # Восстановление MFD из исторических таблиц PostgreSQL
│   ├── test_mfd_new_report.py      # Конвейер генерации обновленного отчета MFD
│   ├── test_sas_report_generator.py # Тесты светофорных обоснований Smart Analysis System
│   ├── test_sas_data_transducer.py # Преобразователь телеметрии SAS
│   ├── test_sas_helpers.py         # Математические расчетные модули SAS
│   ├── test_sas_mfd_db_cache.py    # Кэширование базы данных MFD в подсистеме SAS
│   ├── test_semantic_transducer_device.py # Офлайн-преобразователь SLM и распределение VRAM
│   ├── test_planning_view.py       # Тесты графического интерфейса планировщика Planning View
│   ├── test_planning_architecture.py # Презентер холста планирования и обработчики экспорта
│   ├── test_planning_export_handler.py # Экспорт планов координации в CSV
│   ├── test_planning_panel_presenter.py # Презентер панели управления планированием
│   ├── test_live_canvas_map_widget.py # Высокопроизводительный холст отрисовки дорог и светофоров
│   ├── test_map_interaction_precision.py # Математика зума, сдвиг координат и кэш кликов по улицам
│   ├── test_map_event_router_precision.py # Разрешение конфликтов клика между светофором и улицей
│   ├── test_interactive_map_precision.py # Точность касания интерактивной карты и попадание в слой
│   ├── test_planning_map_sync.py   # Радиус клика PlanningMapRenderer и синхронизация холста
│   ├── test_live_data_provider_ipc.py # Потоковая передача через очереди IPC LiveDataProvider
│   ├── test_watchdog.py            # Логика пульса Watchdog и системные таймеры процессов
│   ├── test_consolidation_purge.py # Консолидация дельта-хранилища гидродинамики
│   ├── test_csv_template_export_import.py # Импорт/экспорт шаблонов контроллеров в CSV
│   ├── test_db_schema_isolation.py # Изоляция схем базы данных при параллельном тестировании
│   ├── test_infrastructure_client.py # Клиент анализа инфраструктурных обоснований
│   ├── test_intersection_state_manager.py # Отслеживание фаз по множеству перекрёстков
│   ├── test_main_components.py     # Базовые компоненты центрального контроллера
│   ├── test_manual_override_hft.py # Высокочастотное ручное переопределение фаз
│   ├── test_pushdown_query.py      # Выполнение pushdown SQL-запросов к аналитическим таблицам
│   ├── test_tls_state_provider.py  # Провайдер фазовых состояний светофорных объектов
│   ├── test_ui_main_orchestrator.py # Тестирование главного оркестратора интерфейса
│   ├── test_window_manager.py      # Управление жизненным циклом десктопного окна
│   ├── test_population_manager_pbt.py # Изоляция когорт Intra-Phase PBT и защита от сбоев размерностей
│   ├── test_performance_margin_calculator.py # Маржа выпуска по гидродинамике и телеметрия детства
│   ├── test_reward_weights_calculator.py # Физическая балансировка наград (время проезда HCM)
│   ├── test_maturity_pacing_calculator.py # Автопейсинг длительности эпизодов по топологии сети
│   ├── test_yellow_schedule_manager.py # Оценка расписания ночного желтого мигания
│   └── test_yellow_schedule_card.py # Карточка UI расписания желтого мигания и диапазоны времени
│
└── integration/                    # Сквозные интеграционные тесты системы (5 модулей)
    ├── test_system_integration.py    # Полный цикл от приема телеметрии gRPC до выдачи фазы
    ├── test_gateway_ipc_pipeline.py  # Конвейер IPC по анонимным пайпам NDJSON шлюза на Go
    ├── test_hft_performance_sla.py   # Валидация субмиллисекундного SLA цикла принятия решений HFT
    ├── test_postgres_migrations.py   # Миграции схем PostgreSQL Alembic и откат изменений
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
