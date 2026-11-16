---
tags: [moc, hub, docs, obsidian, carina, index]
aliases: [CARINA MOC, Главный хаб документации, Индекс документации, База знаний]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# Главный технический хаб документации CARINA
### Центральный индекс и база знаний многоагентной архитектуры
*Noxfort Systems — A State Of Art Company*

</div>

Добро пожаловать в библиотеку технической документации **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture). Спроектированная как высокопараллельная высокочастотная экосистема глубокого обучения с подкреплением (DRL) для адаптивного управления светофорными сетями в реальном времени, CARINA объединяет нейро-символический искусственный интеллект, аппаратное управление через gRPC на субмиллисекундных скоростях и межпроцессную изоляцию уровня операционной системы.

Данный главный индекс документации предназначен для ведущих инженеров-разработчиков, академических исследователей, муниципальных инженеров организации дорожного движения и системных интеграторов. Документация полностью совместима как с **GitHub**, так и с **[Obsidian](https://obsidian.md/)**.

---

## 🗺️ Карта кодовой базы и иерархия каталогов

```text
CARINA_CORE/
├── carina.py                   # Главный оркестратор (SingleInstanceLock, ProcessManager, UI/Tray)
├── ARCHITECTURE.md             # 8-процессная архитектурная схема и топология IPC
├── pyproject.toml              # Инструменты сборки и метаданные проекта
├── requirements.txt            # Зависимости среды выполнения Python
├── .env.example                # Переменные окружения и учетные данные (12-Factor App)
│
├── config/                     # Системы конфигурации
│   ├── settings.ini            # Общесистемные параметры (AI, PBT, Watchdog, MFD, Logging)
│   ├── database/               # Динамические SQL-запросы и схемы (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Правила безопасности и семантической корректности (safety_rules.json, semantic_rules.json)
│   └── templates/              # Многоязычные шаблоны отчетов, MFD, SAS и XAI
│
├── packaging/                  # Герметичное пакетирование Debian и спецификации сборки
│   ├── Dockerfile.build        # Многоэтапный герметичный сборщик (Node, Go, Python, dpkg-deb)
│   └── deb/                    # Файлы контроля Debian, службы systemd и скрипты postinst
│
├── scripts/                    # Скрипты сборки, автоматизации и тестирования с лимитом ОЗУ
│   ├── build_deb.sh            # Контейнеризированный генератор пакетов Debian
│   └── pytest_limited.sh       # Запускатор Pytest с лимитом ОЗУ (cgroup v2 / ulimit, макс. 2 ГБ)
│
├── proto/                      # Спецификации протокола gRPC
│   └── synapse_hft.proto       # Описания Protobuf для высокочастотной телеметрии и управления
│
├── docs/                       # Комплексная база знаний
│   ├── CARINA_MOC.md           # Главный хаб документации (Этот файл)
│   ├── index.md                # Точка входа MkDocs и портал
│   ├── ARCHITECTURE.md         # 8-процессная архитектурная схема и топология IPC
│   ├── EVP_AND_PREEMPTION.md   # Приоритет спецтранспорта (EVP), Go Web Gateway и видеостена CCO
│   ├── API_REFERENCE.md        # Протокол Synapse HFT gRPC и схемы очередей IPC
│   ├── RESEARCH_NOTES.md       # Математические модели PPO-TCN, PAE, GATv2 и учебная программа DA SILVA
│   ├── HARDWARE_DRIVERS.md     # Полевые контроллеры: интеграция NTCIP 1202, UTMC2 и SNMP
│   ├── SAFETY_AND_WATCHDOG.md  # Брандмауэр безопасности Guardian, правила вето и Watchdog
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # Светофорные обоснования MUTCD / FHWA 1, 2, 3, 4
│   ├── MFD_AND_ANALYTICS.md    # Макроскопическая фундаментальная диаграмма (MFD) и динамика плотности
│   ├── DATABASE_AND_SCHEMAS.md # Уровень хранения, асинхронное дельта-сжатие и SQL-схемы
│   ├── XAI_AND_SAS.md          # Объяснимый ИИ, интегрированные градиенты Captum и аналитика SAS
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # Модульный генератор Word (.docx) по ABNT и формулы OMML
│   ├── SLM_AND_LOCAL_LLM.md    # Локальные офлайн-модели LLM (Qwen3.5 2B / llama.cpp)
│   ├── UI_AND_DASHBOARD.md     # Десктопное приложение Flet, Planning View и архитектура SDS
│   ├── RENDERING_AND_HEATMAPS.md # Векторный рендеринг карт и асинхронные теплокарты плотности
│   ├── SECURITY_AND_AUTH.md    # Учетные записи, хеширование PBKDF2 HMAC SHA-256 с солью и защита от брутфорса
│   ├── DEVELOPER_GUIDES.md     # Настройка окружения, иерархия агентов, параметры и пакетирование
│   ├── TESTING.md              # Набор тестов Pytest, моки контроллеров и валидация покрытия
│   └── DEPLOYMENT_AND_PACKAGING.md # Сборка Docker, демоны Systemd и пакеты Debian
│
├── bin/                        # Скомпилированные нативные бинарные файлы (carina-go)
├── src_go/                     # Аппаратный и веб-шлюз на Go (NTCIP, UTMC, EVP, Web Gateway)
│   ├── cmd/gateway/            # Точка входа шлюза и цикл IPC stdin/stdout NDJSON
│   ├── configs/                # Встроенные JSON-профили OID для NTCIP и UTMC
│   ├── evp_go/                 # Микросекундный диспетчер приоритетного пропуска EVP
│   ├── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
│   └── web_gateway/            # Шлюз HTTP/SSE (порт 2201), сеть Tailscale Mesh и обработчики CCO
├── src_tsx/                    # Веб-приложение оператора центра управления (CCO)
│   └── src_cco/                # React 18, TypeScript, Tailwind CSS, векторные SVG-слои карт, ECharts
├── src/                        # Основной исходный код
│   ├── agents/                 # PPO LocalAgent, GuardianAgent, PAEStateAugmentor и чекпоинты
│   ├── analysis/               # MUTCD WarrantEvaluator, WarrantMath и анализ трафика
│   ├── blocks/                 # Модульный построитель .docx, конвертеры OMML и кэшированные форматтеры
│   ├── central_controller.py   # Высокочастотный сервер телеметрии gRPC и владелец шлюза
│   ├── communication/          # MonitorClient, безопасность HFT gRPC (TLS/mTLS/Bearer) и ThreadSafePipe
│   ├── controller/             # HardwareGatewayCoordinator, ConnectionManager, FenixStageDispatcher и переопределения
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, ActionAuthorizer и PopulationManager
│   ├── database/               # DatabaseEngine, PostgresConnectionPool, SQLite WAL и StepDecisionWorker
│   ├── drivers/                # Прокси шлюза Go, RemoteHardwareDriverProxy, HardwareTelemetryDecoder и мост трапов
│   ├── engine/                 # StepProcessor, BatchedPAEEncoder, FleetBatchInferencer (vmap) и PhysicalActionMasker
│   ├── evp/                    # Приоритет спецтранспорта (EVPService, EVPSnapshotSynchronizer, Kinematics)
│   ├── fenix/                  # Самовосстановление и супервизор процессов F.E.N.I.X. (Supervisor, Runner, Reconciler)
│   ├── handlers/               # Обработчики запросов ИИ, команд интерфейса и команд Watchdog
│   ├── interfaces/             # Разделенные протоколы SOLID (Controller, Drivers, Engine, Repositories)
│   ├── launcher/               # ProcessManager, BackendServiceRegistry, FenixSupervisionLoop и WorkerEntrypoints
│   ├── manager/                # CycleManager, StageTransitionManager, AgentPopulationLoader и ServiceManager
│   ├── maturity/               # MaturityManager, AgentMaturity, PromotionService, Config и Port
│   ├── mfd/                    # Анализатор макроскопической фундаментальной диаграммы (MFD) и воркер
│   ├── models/                 # Унифицированный TCN, ActorCriticNet, iTransformer PAE, QR-D3QN и ST-GATv2 Lite
│   ├── optimizer/              # Популяционное обучение (PBT), оптимизаторы PPO и DQN на хосте в NumPy
│   ├── promotion/              # MaturityPacingCalculator, PerformanceMarginCalculator и PromotionEvaluator
│   ├── rendering/              # StaticMapRenderer, AsyncHeatmapRenderer и внеэкранный mpl_utils
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo, HardwareConnectionRepo и ConnectionCSVStore
│   ├── safety/                 # GuardianPhysicsEstimator, GuardianRiskCalibrator (Noisy-OR), GuardianShadowTrainer и чекпоинты
│   ├── sas/                    # Smart Analysis System (офлайн-анализ инфраструктурных обоснований)
│   ├── sds/                    # Smart Dashboard Service (мост Flet, WebSockets и CCOBroadcastClient с пиннингом)
│   ├── security/               # Изолированная подсистема безопасности (Auth, PBKDF2, Lockdown, репозитории)
│   ├── settings/               # Модульные настройки (интерфейсы SOLID, схемы, INI и .env)
│   ├── slm/                    # Малые языковые модели (Qwen3.5 2B, зондирование VRAM pynvml и slm_process_lock)
│   ├── transports/             # Полиморфные транспорты (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Paths, SumoNetCache и расчет шагов эпизода
│   ├── watchdog/               # Монитор пульса (heartbeat) процессов и отказоустойчивый fallback
│   └── xai/                    # Атрибуция Integrated Gradients, кэшированный построитель отчетов и воркер
│
├── ui/                         # Нативное десктопное приложение на Flet
│   ├── cards/                  # Модульные карточки настроек и телеметрии (RemoteGateway, Hardware, EVP)
│   ├── controllers/            # DashboardDataCoordinator и RemoteGatewaySettingsPersister
│   ├── handlers/               # Обработчики событий, SettingsHandler и нативный SystemTrayHandler
│   ├── views/                  # DashboardView, PlanningView, DiagnosticsView, SettingsView
│   ├── widgets/                # LiveCanvasMapWidget, PlanningControlPanel, MFDViewer, пагинированный AuditLogWidget
│   ├── renderers/              # PlanningMapRenderer, MapVisualSyncer, MapDrawer
│   ├── animators/              # MapAnimator (пауза скрытого окна и контроль dirty-флагов)
│   └── locales/                # Многоязычные словари JSON (pt_br, en_us, es_es и др.)
│
└── tests/                      # Набор Pytest (967 тестов, memory_guard.py) + 46 тестов Go в src_go/
```

---

## 📖 Измерения системы и навигация по базе знаний

### 1. Базовая инфраструктура и драйверы оборудования
- **[Глубокий анализ архитектуры](architecture.md)**: Исчерпывающая техническая схема, описывающая все 8 параллельных микросервисов ОС, изоляцию процессов через `multiprocessing`, каналы IPC Pipe/Queue и цикл выполнения.
- **[Драйверы контроллеров и физическое оборудование](hardware_drivers.md)**: Спецификации скомпилированного аппаратного шлюза на Go (`carina-go`), бессетевого IPC через стандартные пайпы NDJSON, стандартов NTCIP 1202 (ASC), британского UTMC / UTMC2, клиента SNMP v2c/v3, пула соединений и детерминированного возврата оборудования в аварийный режим (fail-safe).
- **[Справочник API и протокол HFT](api_reference.md)**: Полные спецификации интерфейса gRPC `Synapse HFT`, внешней телеметрии Monitor (MQTT/HTTP), конечных точек метрик Prometheus (порт 8001) и схем очередей IPC.
- **[Архитектура БД и схемы данных](database_and_schemas.md)**: Спецификации воркеров `DatabaseWorker`, `StepDecisionWorker`, пула соединений, конфигурации 12-Factor `.env` и дельта-хранилища PostgreSQL (сокращение объема на 97.9%).
- **[Безопасность и аутентификация](security_and_auth.md)**: Управление учетными записями пользователей, хеширование `PBKDF2 HMAC SHA-256` с солью, защита от перебора паролей (брутфорса) и ролевая модель доступа.
- **[Модульная архитектура настроек](architecture.md#4-модульная-архитектура-настроек-srcsettings)**: Подсистема конфигурации по принципам SOLID, разделяющая схемы, персистентность в INI и секреты 12-Factor `.env`.
- **[Полиморфный мониторинг и транспорты](architecture.md#5-полиморфная-архитектура-мониторинга-и-транспорта-srctransports)**: Потоковая передача телеметрии и инцидентов через брокеры MQTT и облачные REST/Ngrok-эндпоинты HTTP/HTTPS.

### 2. Искусственный интеллект и нейро-символическая безопасность
- **[Нейросетевые исследования и формулы](research_notes.md)**: Строгие математические формулировки для PPO-TCN, латентных проекций $Z$ предиктивного автоэнкодера (PAE), раздельных потоков ценности и преимущества Dueling DQN-TCN, графового внимания ST-GATv2 Lite и учебной программы созревания DA SILVA.
- **[Архитектура безопасности, Watchdog и F.E.N.I.X.](safety_and_watchdog.md)**: Реестр символических правил вето (SR-00—SR-06), пороги нейросетевого вето PAE, мониторинг пульса Watchdog в реальном времени (< 500 мс) и автономное воскрешение процессов F.E.N.I.X. с чистым согласованием граничных состояний.
- **[Объяснимый ИИ (XAI), SAS и анализ MFD](xai_and_sas.md)**: Принципы работы модульного конвейера XAI, атрибуция интегрированных градиентов Captum и муниципальный криминалистический аудит.
- **[Генератор аналитических отчетов и модуль Word](report_blocks_and_templates.md)**: Автоматизированная генерация отчетов Word (`.docx`) по стандарту ABNT NBR 14724 с нативными формулами Office Math Markup Language (OMML).
- **[Компактные языковые модели (SLM)](slm_and_local_llm.md)**: Локальный 100% автономный инференс LLM (Qwen3.5 2B / llama.cpp), генерирующий подробные текстовые заключения без внешних облачных зависимостей.

### 3. Физика транспортных потоков, обоснования и графика
- **[Светофорные обоснования организации движения](traffic_engineering_warrants.md)**: Автоматическая оценка нормативных критериев MUTCD / FHWA (критерии 1—4) и инфраструктурных условий.
- **[Макроскопическая фундаментальная диаграмма и динамика потоков](mfd_and_analytics.md)**: Физика соотношения потока и плотности сети, критическая плотность ($K_{crit}$), периметральное дозирование (gating), обнаружение падения пропускной способности (capacity drop) и кэширование фильтра инцидентов.
- **[Рендеринг карт и теплокарты](rendering_and_heatmaps.md)**: Офлайн-парсинг векторных карт дорожных сетей SUMO `.net.xml` и асинхронные теплокарты ядерной оценки плотности (KDE).

### 4. Десктопный фронтенд и эксплуатация
- **[Пользовательский интерфейс и Smart Dashboard Service](ui_and_dashboard.md)**: Архитектурный разбор нативного десктопного интерфейса на Flet, векторный планировщик Planning View, сокетная блокировка единственного экземпляра (порт 42123) и потоковая передача телеметрии по WebSockets.
- **[Руководства разработчика и интеграция](developer_guides.md)**: Руководство по развертыванию сред, изменению конфигурации, расширению алгоритмов агентов и сборке пакетов.
- **[Тестирование и валидация](testing.md)**: Инструкции по запуску `pytest` (967 автоматизированных тестов в 192 модульных, 8 интеграционных и 4 корневых файлах + 46 тестов Go), ограничению ОЗУ через `scripts/pytest_limited.sh`, мокированию драйверов и валидации правил вето Guardian.
- **[Развертывание, пакетирование и контейнеризация](deployment_and_packaging.md)**: Инструкции по контейнеризации в Docker (`Dockerfile`), службам Systemd и пакетам Debian `.deb`.

### 5. Приоритетный пропуск спецтранспорта и удаленное управление (EVP / CCO)
- **[Приоритет спецтранспорта и удаленное управление](evp_and_preemption.md)**: Спецификации модуля приоритетного пропуска экстренных служб (EVP), соответствие стандартам CONTRAN/MUTCD, кинематика на основе формулы гаверсинусов, двухфакторная триггерная логика, 45-секундный аварийный таймер watchdog, диспетчер преемпции на Go, безопасная ячеистая сеть Tailscale Funnel и веб-интерфейс оператора центра управления (CCO) (`src_tsx/src_cco`).

---

> 💡 **Граф знаний Obsidian:** Данный комплект документации полностью оптимизирован для [Obsidian](https://obsidian.md/). Откройте корневой каталог `CARINA_CORE` как хранилище (Vault) Obsidian для интерактивной навигации по графу связей и обратным ссылкам.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
