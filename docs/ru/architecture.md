---
tags: [architecture, core, system, gatv2, pae, pbt, amp, multiprocessing]
aliases: [Архитектура системы, Схема мультипроцессинга, Системный обзор]
---

# 🏛️ CARINA: Системная схема и архитектура мультипроцессинга

Данный документ описывает внутреннюю инженерную архитектуру экосистемы CARINA. В нем подробно рассматриваются 8 параллельных микросервисов операционной системы, каноническая топология глубоких нейронных сетей (LocalAgent PPO-TCN, GuardianAgent D3QN и StrategistAgent ST-GATv2 Lite), модуль топологического автомасштабирования `TopologicalScaler`, драйверы физических дорожных контроллеров и асинхронное ядро дельта-хранения в PostgreSQL.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🚨 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md) | 🚦 См. [Драйверы оборудования](hardware_drivers.md) | 🧠 См. [Нейросетевые формулы](research_notes.md) | 🛡️ См. [Безопасность и Watchdog](safety_and_watchdog.md)

---

## 1. Модель параллелизма микросервисов на уровне процессов ОС

Глобальная блокировка интерпретатора Python (Global Interpreter Lock — GIL) не позволяет многопоточным вычислениям нейросетей, ограниченным CPU, и интенсивным операциям ввода-вывода выполняться в истинном параллелизме. Для достижения субмиллисекундных задержек управления CARINA использует **модель микросервисов на основе независимых процессов ОС (`multiprocessing`)**, оркестрируемую [`carina.py`](../../carina.py) и [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py) (модуляризованную с помощью [`backend_service_registry.py`](../../src/launcher/backend_service_registry.py), [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py) и [`worker_entrypoints.py`](../../src/launcher/worker_entrypoints.py)), в сочетании с промышленным **аппаратным и веб-шлюзом на Go** (`bin/carina-go`), исключительным владельцем которого является `CentralController` (`CARINA_GATEWAY_ROLE=owner`):

```mermaid
graph TD
    Launcher["Оркестратор carina.py / Системный трей - remote"] -->|Запускает и контролирует| PM[ProcessManager]

    PM --> CC[1. Процесс CentralController - owner]
    PM --> AI[2. Движок AI_Process - remote]
    PM --> WD[3. Процесс Watchdog]
    PM --> SDS[4. Сервис панели SDS - remote]
    PM --> SAS[5. Сервис анализа SAS]
    PM --> DB[6. StepDecisionWorker и DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Движок MFD_Worker]

    CC <-->|ThreadSafePipeConnection| AI
    CC -->|Очередь wd Heartbeats| WD
    WD -->|Очередь fenix| PM
    AI -->|Очередь db| DB
    CC -->|Очередь sds| SDS
    CC -->|Очередь sas| SAS
    CC -->|Очередь mfd_trigger| MFD
    MFD -->|Очередь mfd_results| CC
    SAS -->|Очередь sas_results| CC
    XAI -->|Журналы HFT на диске| AI

    CC <-->|NDJSON Stdin/Stdout| GW["Шлюз Go carina-go"]
    GW --> NTCIP["Контроллеры NTCIP 1202 / UTMC2 UDP 161"]
    GW --> WebGW["Веб-шлюз Go Порт 2201 / TLS / Tailscale"]
    WebGW --> CCO["Веб-карта CCO React/TSX src_tsx"]
    WebGW <--|POST 204 Токен аутент.| EVP["GPS-антенны EVP Порт 8085 / 2201"]
```

### 1.1 Единое владение шлюзом (`CARINA_GATEWAY_ROLE`) и замкнутая синхронизация оборудования
Для предотвращения расщепления (split-brain) опроса SNMP, конфликтов порта трапов `162` и дублирования дочерних процессов `carina-go` между процессами-воркерами:
- **Процесс-владелец (`CARINA_GATEWAY_ROLE=owner`):** Задается строго внутри [`execute_controller_process`](../../src/launcher/worker_entrypoints.py) для `CentralController`. Он запускает [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (состоящий из `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` и `TailscaleGatewayAdapter`), который монопольно владеет `bin/carina-go`, локальными SNMP-соединениями `HardwareConnectionManager` и приемом телеметрии `EVPService`.
- **Удаленные процессы-зеркала (`CARINA_GATEWAY_ROLE=remote`):** Задается в [`carina.py`](../../carina.py), [`src/main.py`](../../src/main.py) (`AI_Process`) и [`dashboard_worker.py`](../../src/sds/dashboard_worker.py). Удаленные процессы синхронизируют зеркалированный статус по IPC (`RemoteHardwareDriverProxy` через [`remote_proxy_synchronizer.py`](../../src/drivers/remote_proxy_synchronizer.py)) и перенаправляют действия/преемпции (`ai_hardware_cmd`, `ai_evp_preempt`, `set_hardware_connection`) через [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Замкнутая аппаратная телеметрия (`HardwareTelemetrySynchronizer`):** Внутри цикла ИИ модули [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) и [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) декодируют живые битовые маски сигналов NTCIP 1202 / UTMC2 (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) в 0-индексированные стадии SUMO для истинного замкнутого управления и согласования передачи управления F.E.N.I.X.

---

## 2. Архитектура глубокого обучения

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │  Автоопределение узлов сети (N) -> Разм. скрытого слоя (32/64/128/256), │
    │                         Число голов (2/4/8/16)                          │
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │     LOCAL AGENT (PPO)       │           │   STRATEGIST AGENT (GRAPH)  │
     │     Базовый модуль TCN      │           │   Координатор ST-GATv2 Lite │
     │  (Субсекундное управление)  │◄──────────┤    (Зелёные волны улиц)     │
     └──────────────┬──────────────┘Вектор конт.└──────────────┬──────────────┘
                    │                                         │
                    │ Предложенное действие                   │ Контекст сети
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │ Нейро-символический щит безопасности, защита от заторов и вето трафика│
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 Модуль ST-GATv2 Lite (`src/models/st_gatv2_lite.py` и `src/engine/strategic_coordinator.py`)
- **Назначение:** Пространственная синхронизация магистральных «зелёных волн» между соседними перекрёстками в графе улично-дорожной сети с помощью `TemporalConvNetLite` (`GroupNorm(1, C)` + `SiLU` + `TemporalAttentionPool`) и двух последующих остаточных слоев `GATv2Conv`.
- **Онлайн-самообучение и головы CTDE:** Включает вспомогательную голову прогнозирования на следующий шаг (`pred_head`) и кооперативную голову глобальной ценности (`global_critic_head`). [`StrategicCoordinator`](../../src/engine/strategic_coordinator.py) агрегирует последовательности узлов с помощью немодифицирующих вызовов [`StateExtractor.peek_state()`](../../src/engine/state_extractor.py), благодаря чему вторичное чтение графа никогда не искажает скользящие средние (EMA) модуля `HistoricalAggregator`.
- **Децентрализованная координация:** Агент-Стратег периодически вычисляет пространственно-временной тензор контекста по всей сети и передает его Локальным агентам через остаточный вентиль `tanh` (`PAEStateAugmentor`), обеспечивая возникновение эмерджентных «зелёных волн» без централизованных уязвимых единых точек отказа.

### 2.2 Универсальный Action-Conditioned iTransformer PAE (`src/models/pae.py`)
- **Назначение:** Общая физическая модель мира высокой емкости, проецирующая будущую пространственно-временную динамику ($t + \Delta t$) для гетерогенных топологий перекрёстков.
- **Архитектура iTransformer и неопределенность:** Использует поканальную нормализацию RevIN + эмбеддинг масштаба `[mean, std]`, инвертированные слои кодировщика Transformer по переменным датчиков, латентный пулинг с перекрестным вниманием и `key_padding_mask` (`valid_dims`), чтобы дополненные нулями полосы не загрязняли латентные векторы, бинарное обусловливание действием (`0 = ADVANCE`, `1 = KEEP`) и оценку гетероскедастичной неопределенности (`decode_with_uncertainty -> (mean, log_var)`) с опциональным прогревом `torch.compile` (`torch_compile_helper.py`).
- **Однопроходное пакетное кодирование:** Выполняется один раз за шаг симуляции по всем перекрёсткам через [`BatchedPAEEncoder`](../../src/engine/batched_pae_encoder.py) и переиспользуется в [`PPOOptimizer`](../../src/optimizer/ppo_optimizer.py) на протяжении эпох обучения через `precomputed_latents`.

### 2.3 Тактическая векторизация и дистрибутивная безопасность Guardian (`src/engine/`, `src/safety/`)
- **Унифицированный причинный бэкбон TCN (`src/models/tcn_backbone.py`):** Заменяет устаревший `weight_norm` на `TemporalConv1d`, причинную поканальную нормализацию `GroupNorm(1, C)`, `SiLU`, ортогональную инициализацию и `TemporalAttentionPool`. `ActorCriticNet` выдает необработанные логиты FP32 (`forward_logits`), маскируемые напрямую через [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py) (обеспечивая соблюдение клиренса желтого/всекрасного, минимального и максимального зеленого).
- **Однородный инференс `torch.vmap` (`src/engine/fleet_batch_inferencer.py`):** Группирует агентов `LocalAgent` по архитектурной сигнатуре и выполняет векторизованные прямые проходы через `torch.func.stack_module_state` + `torch.vmap`, упаковывая скаляры в CPU-буферы NumPy (`last_cpu_decisions`), а также использует расчет GAE в NumPy на хосте в `PPOOptimizer` и резидентные в ОЗУ CPU буферы `ReplayMemory` / `StateReplayMemory` (`pin_memory`, кэш `_max_priority` за $O(1)$, `push_batch`).
- **Калиброванный QR-D3QN и Guardian Noisy-OR (`src/safety/`):** `D3QN_TCN` моделирует `num_quantiles = 32` для каждого бинарного действия для оценки хвостового риска $\text{CVaR}_{0.20}$. [`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py) нормирует насыщение входящих ребер на реальную вместимость полос и проецирует состояние на горизонт клиренса $H = \text{yellow} + \text{all\_red}$; [`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py) выполняет логистическую калибровку с настройкой по $F_2$-мере и некомпенсаторное **слияние Noisy-OR**. [`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) обучает Guardian исключительно на стадии `Maturity.CHILD`, затем при выпуске вызывает `freeze_for_deployment()` и сохраняет `guardian_{tl_id}.pth` через [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py).

### 2.4 Автомасштабирование топологии $O(1)$ (`src/utils/topo_scaler.py`)
- **Алгоритмическое масштабирование:** Автоматически определяет масштаб сети ($N$ светофорных объектов) и автономно подбирает размерности нейросетей степенями двойки, оптимизированными под аппаратные блоки NVIDIA TensorCores:
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$ (например, агломерация Лондрина)
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$ (Сверхкрупные мегаполисы)

### 2.5 Ускорение Universal AMP и TensorCore
- Все прямые проходы нейросетей выполняются внутри контекста `torch.amp.autocast`, что включает нативное аппаратное ускорение FP16/TF32 на тензорных ядрах NVIDIA и ограничивает общее потребление видеопамяти (VRAM) на уровне всего лишь **~20 МБ** для базовых моделей.

---

## 3. Персистентные данные и дельта-сжатие хранилища

CARINA реализует асинхронное ядро персистентности с использованием **RLE дельта-сжатия** и потокобезопасного пула соединений в базах данных PostgreSQL и SQLite:
- **`step_decisions`**: Сохраняет предложенные действия, вето безопасности Guardian и таймеры фаз, отправляемые через [`StepDecisionWorker`](../../src/database/step_decision_worker.py) по неблокирующим очередям в оперативной памяти (накладные расходы $< 0.001\text{ мс}$).
- **`edge_dictionary`**: Сопоставляет длинные строковые названия дорожных сегментов 4-байтовым целочисленным идентификаторам для компактного индексирования.
- **Пул соединений и прагмы (`src/database/connection_pool.py`):** Предоставляет `PostgresConnectionPool` (`psycopg2.pool.ThreadedConnectionPool`, `minconn=1, maxconn=16`), детерминированный менеджер контекста `db_transaction`, настройку SQLite WAL (`busy_timeout=30000`, `synchronous=NORMAL`, `temp_store=MEMORY`, `journal_mode=WAL`), опциональный режим `enable_step_worker=False` для воркеров только на чтение (`XaiWorker`), параметризованные запросы `make_interval(...)` и автоматическую очистку телеметрии EVP старше 168 часов.
- **Сокращение объема хранения:** Достигается **сокращение объема дискового пространства на 97.9%** (~380 МБ/сутки для столичной сети из 200 перекрёстков).

Подробные схемы базы данных и SQL-запросы см. в документе [Архитектура БД и схемы данных](database_and_schemas.md).

---

## 4. Модульная архитектура настроек (`src/settings/`)

В строгом соответствии с принципами **единственной ответственности (Single Responsibility)** и **разделения интерфейсов (Interface Segregation)** парадигмы SOLID, управление конфигурацией в CARINA разделено на независимые, изолированно тестируемые компоненты:

```text
       ┌────────────────────────────────────────────────────────┐
       │             SettingsService (Оркестратор)              │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(Валидация и   │     │& Write       │ │(Файловый ввод/ │ │(Секреты .env в       │
│ Карта секций) │     │(Интерфейсы)  │ │ вывод INI)     │ │ концепции 12-Factor) │
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ Фасад обратной совместимости
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`):** Нормативный реестр, определяющий сопоставление ключей секциям конфигурации (включая ключи TLS/токенов gRPC `[SYNAPSE]` и ключи TLS/CORS/порта `[REMOTE_GATEWAY]`), значения по умолчанию и правила проверки типов данных.
- **`IniFileStorage` (`src/settings/ini_storage.py`):** Отвечает за чтение и персистентную запись файла `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** Загружает конфиденциальные секреты инфраструктуры из файла `.env` с помощью `python-dotenv` с резервным парсингом файла при сбоях (включая `CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`, `CARINA_CCO_ALLOWED_ORIGIN`, `CARINA_GATEWAY_TLS_*`, `CARINA_GATEWAY_PORT`, `CARINA_TRAP_PORT`).
- **`SettingsService` (`src/settings/service.py`):** Базовый сервис, управляющий извлечением конфигурации, валидацией и сериализацией.
- **`SettingsManager` (`src/utils/settings_manager.py`):** Фасад полной обратной совместимости, гарантирующий нулевую регрессию для унаследованных модулей системы.
- **Протоколы SOLID (`src/interfaces/`):** Разделенные интерфейсы в `controller.py`, `drivers.py`, `engine.py` и `repositories.py`, развязывающие слои координатора, шлюза, драйверов, PAE, маскирования действий и персистентности.

---

## 5. Полиморфная архитектура мониторинга и транспорта (`src/transports/`)

CARINA оснащена **полиморфным транспортным уровнем телеметрии и инцидентов**, обеспечивающим удаленный мониторинг в реальном времени через локальные брокеры MQTT, удаленные вебхуки, облачные REST API или туннелирующие шлюзы (например, Ngrok):

```text
IncidentReporter / TelemetryLoop
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (Фасад-Одиночка Singleton)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (Фабрика с автоматическим разрешением эндпоинта)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│(Локальный/Сетевой брокер) │             │ (REST API / Облако / Ngrok) │
│ - Хост:Порт (напр. :1883) │             │ - http:// или https://     │
│ - QoS 0/1 Телеметрия      │             │ - Постоянная HTTP-сессия  │
│ - Топики: noxfort/telem/  │             │ - Экспоненциальный retry  │
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 Абстракция транспорта (`BaseMonitorTransport`)
Определяет строгий контракт для всех модулей экспорта телеметрии:
- `setup()`: Конфигурирует конечные точки подключения, таймауты и учетные данные.
- `ensure_connected()`: Устанавливает или проверяет сетевое соединение.
- `publish(topic, payload)`: Отправляет полезную нагрузку JSON асинхронно или в выделенных фоновых потоках.
- `disconnect()`: Сбрасывает ожидающие буферы и корректно закрывает сессию связи.

### 5.2 Автоматическое разрешение конечных точек (`endpoint_resolver.py`)
Интеллектуально классифицирует целевой адрес без необходимости явной настройки протокола оператором:
- URL-адреса, начинающиеся с `http://` или `https://` (а также домены, содержащие `ngrok`, `run.app` или `/api/`), инстанциируют `MonitorHttpTransport`.
- Стандартные строки сетевых имен или IP-адресов (`localhost`, `10.0.0.1`, `broker:1883`) инстанциируют `MonitorMqttTransport`.

### 5.3 Дедупликация инцидентов и фильтрация оповещений (`src/drivers/`)
- [`IncidentReporter`](../../src/drivers/incident_reporter.py) рассылает уведомления об изменении статуса подключения контроллеров и аппаратных ошибках внешним системам мониторинга.
- [`IncidentFilter`](../../src/drivers/incident_filter.py) предотвращает шторм однотипных алертов, кэшируя хэши активных инцидентов с подавлением дребезга по таймстемпам и сохраняя файл `.carina_incident_filter_cache.json` между перезапусками системы.

---

## 6. Высокопроизводительный аппаратный шлюз на Go (`src_go/`)

Для обеспечения промышленного уровня надежности, субмиллисекундного сетевого детерминизма и полного исключения конкуренции за GIL при полевом развертывании CARINA делегирует всё сетевое взаимодействие с контроллерами (порты UDP 161 и 162) специализированному скомпилированному **аппаратному шлюзу на Go** (`bin/carina-go`, собираемому из `src_go/`):

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │ [Synapse Perception]  <-- gRPC (50051) -->  [Камеры]   │
       │            │                                           │
       │      [Нейросетевой движок AI]                          │
       │            │                                           │
       │    [Супервизор безопасности]                           │
       │            │                                           │
       │ [HardwareConnectionManager] (Оркестратор Python)       │
       │            │                                           │
       │   [GoGatewayClient] (Управление подпроцессом каналов)  │
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout (Line-Delimited JSON)
                    │ НОЛЬ ОТКРЫТЫХ СЕТЕВЫХ ПОРТОВ НА ХОСТЕ
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │           CARINA HARDWARE GATEWAY (Демон Go)           │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [NDJSON IPC Сканер и конкурентный писатель]       │
       │  +-- [Реестр подключений HardwareManager]              │
       │  +-- [Атомарный Fail-Safe при EOF / SIGPIPE]           │
       │  +-- [Движок пульса: time.Ticker на каждый объект]     │
       │  +-- [Диспетчеры протоколов NTCIP 1202 и UTMC2]        │
       │  +-- [Пул SNMP-клиентов GoSNMP (UDP 161)]              │
       │  +-- [Сервер TrapListener (UDP 162)]                   │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Трапы)
                            ▼                  ▼
                    [Дорожный контр.]   [Дорожный контр.] ...
```

### 6.1 Ключевые архитектурные свойства
- **Единое владение процессом и отсутствие локальных портов управления:** Только `CentralController` (`CARINA_GATEWAY_ROLE=owner`) запускает `bin/carina-go`. Канал управления между Python и Go работает строго через анонимные пайпы ОС (`pipe(2)` NDJSON `stdin`/`stdout`), в то время как `AI_Process` и `UI` зеркалируют статус через [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py).
- **NTCIP 1202, UTMC2 и SNMPv3 USM:** Реализует канонические OID NTCIP 1202 (`.4.1.*` статус / `.5.1.*` управление), OID запросов и стадий UTMC2, декодирование целочисленных и `OCTET STRING` битовых масок `GetBitmask` (`src_go/pkg/snmp/codec.go`), полную поддержку SNMPv3 USM (`NoAuthNoPriv`, `AuthNoPriv`, `AuthPriv`) и переопределения OID через `config_path` для каждого перекрёстка, сохраняемые в `hardware_controller_connections.snmp_config` и CSV-таблицах.
- **Бинарный декодер SNMP-трапов и межзеленая защита:** [`snmp_decoder.go`](../../src_go/pkg/traplistener/snmp_decoder.go) декодирует бинарные пакеты SNMPv1/v2c/v3 Trap и Inform, а [`HardwareStageActuator`](../../src/drivers/hardware_stage_actuator.py) пропускает конфликтующие команды удержания во время межзеленых интервалов желтого/всекрасного.
- **Атомарный безаварийный сброс (Fail-Safe) и восстановление:** При `EOF`/`SIGPIPE` шлюз Go вызывает `ShutdownAll()` по SNMP; при таймаутах Watchdog во время работы `EmergencyReleaseControlAll()` приостанавливает heartbeat-сигналы и снимает удержания, сохраняя драйверы и слушатель трапов, чтобы команда `resume_control` (`ResumeControlAll()`) могла восстановить управление без переоткрытия сокетов.
- **Бесшовная адаптация (`GoTrafficDriverProxy` и `RemoteHardwareDriverProxy`):** Оба прокси — локальный и удаленный — реализуют контракт `BaseTrafficDriver` (LSP), делая оркестрацию оборудования полностью прозрачной для `ActionSupervisor` и `StepProcessor`.

---

## 7. Супервизор процессов F.E.N.I.X. и подсистема восстановления после сбоев (`src/fenix/`)

CARINA интегрирует архитектурный компонент **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) для обеспечения непрерывного круглосуточного автономного самовосстановления движка нейросетевого инференса:

```text
       ┌────────────────────────────────────────────────────────┐
       │              Монитор состояния Watchdog                │
       └───────────────────────────┬────────────────────────────┘
                                   │ Таймаут / Пропущенный пульс
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             FenixSupervisor (Оркестратор)              │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- Скользящее окно задержек  │ │- Жизненный цикл процесса│
       │- Лимитер квоты перезапусков│ │- SIGTERM / SIGKILL      │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ Перезапуск
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- Телеметрия FROZEN_SYNC │
                                      │- FenixStageDispatcher   │
                                      │- Бесконфликтный захват  │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`) и `fenix_supervision_loop.py`:** Координируют принудительное завершение подпроцессов, задержки восстановления, перезапуск дочернего процесса и подтверждение `HANDOVER_COMPLETE`.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** Вычисляет экспоненциальные задержки и контролирует лимиты частоты перезапусков, защищая систему от лавинообразных циклов падения.
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** Низкоуровневое управление процессами, гарантирующее детерминированную изоляцию и чистое завершение по сигналам SIGTERM/SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`) и `FenixStageDispatcher` (`src/controller/fenix_stage_dispatcher.py`):** Удерживают воскрешенный движок ИИ в режиме `FROZEN_SYNC`, запрашивают реальные фазы контроллера через `HardwareTelemetryDecoder` и инициируют `fenix_post_resurrection` -> `fenix_handover_complete` исключительно на бесконфликтных границах фаз.

---

## 8. Жизненный цикл агентов, Intra-Phase PBT и механизм повышения (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA рассматривает популяции политик обучения с подкреплением как эволюционирующий организм, проходящий 3-стадийную программу взросления:

```text
  ┌──────────────────┐       Падение энтропии и пейсинг       ┌──────────────────┐     Энтропия и маржа потока (delta*)     ┌──────────────────┐
  │   СТАДИЯ CHILD   │ ─────────────────────────────────> │   СТАДИЯ TEEN    │ ───────────────────────────────────────> │   СТАДИЯ ADULT   │
  │ (Теневой режим)  │                                    │ (Внепик. автон.) │                                          │(Полная автономия)│
  └────────┬─────────┘                                    └────────┬─────────┘                                          └────────┬─────────┘
           │                                                       │                                                             │
           ▼                                                       ▼                                                             ▼
  [Изоляция от PBT]                                       [Intra-Phase PBT]                                             [Intra-Phase PBT]
  [Анализ гидродинамики]                                  (Строго TEEN <-> TEEN)                                        (Строго ADULT <-> ADULT)
  [Недельный минимум]                                     [Теневой режим в пики]                                        [Активный режим 24/7]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`):** Центральный сервис приложения и фасад, координирующий оценку зрелости агентов совместно с сущностью `AgentMaturity`, `MaturityConfig` и `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`):** Реализует алгоритм внутрифазового эволюционного обучения **Intra-Phase Population-Based Training**. Клонирование и мутация весов разрешены только внутри однородной когорты (`TEEN` только с `TEEN`, `ADULT` только с `ADULT`), тогда как агенты `CHILD` полностью изолированы от мутаций. Включает верификацию размерностей тензоров для предотвращения сбоев на гетерогенных перекрёстках.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`):** Выполняет строгую проверку информационной энтропии политики Шеннона, минимальной продолжительности эпизодов и целевых показателей качества управления.
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`):** Динамически рассчитывает шаги в эпизоде на основе топологии дорожной сети (объединение встречных направлений улиц, исключение внутренних соединителей `:` и применение сублинейной релаксации $\sqrt{N}$ и $D_{\text{km}}$), вычисляя неприкосновенный минимум в 1 полную неделю ($E_{\text{week}}$ эпизодов при $\Delta t = 250\text{ мс}$).
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`):** Отслеживает и атомарно сохраняет покрытие всех 168 часов недели ($7\text{ дней} \times 24\text{ часа}$), гарантируя устойчивость к паузам и перезапускам без потери истории созревания.
- **`ActionAuthorizer` (`src/core/action_authorizer.py`):** Ограничивает физическое управление агента `TEEN`, принудительно активируя теневой режим в классические часы пик (06:30-09:00 и 17:00-19:30 по будням) или по динамическому расписанию Synapse.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`):** Координирует темпоральный пейсинг, интегрируя `EpisodeStepCalculator` и обеспечивая соблюдение неприкосновенного порога безопасности ($t_{\min} = \max(E_{\text{week}}, \text{конфигурация})$).
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`):** Непрерывно вычисляет динамическую маржу превосходства $\delta^* \in [3.0\%, 25.0\%]$ на основе эмпирической скорости и плотности транспорта из таблицы `synapse_fluid_dynamics`.

---

## 9. Подсистема физической балансировки наград (`src/engine/reward_weights_calculator.py`)

Для исключения градиентного перекоса, когда суммарное время ожидания в очереди на порядки превосходит пропускную способность перекрёстка, CARINA балансирует уравнение функции вознаграждения в соответствии с законами транспортной гидродинамики Highway Capacity Manual (HCM):

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`):** Вычисляет нормализованные веса функции вознаграждения в момент загрузки топологии дорожной сети (`TopologyManager.load_topology`).
- **`RewardCalculator` (`src/engine/reward_calculator.py`):** Принимает динамические веса через метод `set_reward_weights`, обеспечивая равновесие, при котором стимулирование сброса очереди пропорционально масштабу накопленной задержки транспорта.

---

## 10. Подсистема ночного режима желтого мигания (`src/controller/yellow_schedule_manager.py`)

Для обеспечения безопасности и соблюдения нормативных требований в часы минимальной интенсивности ночного движения CARINA включает автономный планировщик желтого мигания:
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`):** Сопоставляет настроенные временные окна (например, с 23:00 до 05:00) с системными часами реального времени, автономно переводя контроллеры в режим желтого мигания и бесшовно возвращая их под адаптивное управление ИИ на границах интервалов.
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`):** Элемент графического интерфейса, позволяющий операторам включать/выключать расписания, настраивать временные диапазоны и гибко назначать режимы как для отдельных объектов, так и для всей агломерации.

---

## 11. Подсистема приоритетного пропуска экстренных служб (EVP) (`src/evp/`, `src_go/evp_go/`)

Для мгновенного формирования «зелёных коридоров» каретам скорой помощи, пожарным расчетам и оперативным службам в соответствии с бразильскими нормативами CONTRAN № 960, статьей 29 CTB и рекомендациями MUTCD, CARINA оснащена специализированной подсистемой приоритетного пропуска:

```text
 GPS-антенна / Маяк        Go Web Gateway (:2201 / :8085)       EVPService (src/evp/)
          │                             │                                   │
          │── POST /api/v1/evp/telemetry─>│                                 │
          │   (HTTP 204 No Content)     │── Поток NDJSON / Память ─────────>│
          │                             │                                   ├── Кинематика (WGS84 Гаверсинусы)
          │                             │                                   ├── Зона входа (60м <= d <= 160м)
          │                             │                                   └── Проверка работы сирены
          │                             │                                           │
          │                             │                                           ▼
          │                             │                                 SafetyAuditor (Правило #0)
          │                             │                                 (Клиренс -> ACTION_HOLD)
          │                             │                                           │
          │<───── Зелёный коридор ──────┼── SNMP ascPhaseHold (Go Диспетчер) <─────┘
```

- **Двухфакторный триггер:** Активация приоритета требует одновременного входа машины в зону перекрёстка ($60\text{ м} \le d \le 160\text{ м}$) И включенной спецсирены (`siren_active = True`).
- **Приоритетный перехват SafetyAuditor:** Правило #0 перехватывает команды ИИ, строго соблюдает межзеленые интервалы безопасности (желтый и всекрасный) и удерживает разрешающий сигнал (`ACTION_HOLD = 1`).
- **Защитный таймер CONTRAN Watchdog ($45\text{ с}$):** Безусловно снимает удержание фазы через 45 секунд во избежание коллапса движения на поперечных направлениях.
- **Мгновенный сброс при проезде:** Как только автомобиль пересекает стоп-линию ($d \le 15\text{ м}$), приоритетный режим немедленно деактивируется.

Полные технические спецификации приведены в руководстве [Приоритетный пропуск спецтранспорта (EVP)](evp_and_preemption.md).

---

## 12. Веб-архитектура оператора центра управления (CCO) и безопасность транспорта (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA предоставляет защищенный веб-центр мониторинга для муниципальных ситуационных видеостен и удаленного контроля:
- **`WebGatewayServer` (`src_go/web_gateway/server.go`, `auth.go`):** Встроенный HTTP/HTTPS-сервер на Go, работающий на порту 2201 (`CARINA_GATEWAY_PORT`). По умолчанию установлен режим `gateway_enabled=False` (возвращает `503 Service Unavailable` до включения), обеспечивает постоянную по времени проверку токенов Bearer/заголовков (`CARINA_CCO_AUTH_TOKEN`, `CARINA_EVP_AUTH_TOKEN`), явные источники CORS (`CARINA_CCO_ALLOWED_ORIGIN`), терминацию TLS (`CARINA_GATEWAY_TLS_CERT`/`KEY`), потоковую рассылку SSE (`/cco/stream`), эндпоинты топологии (`/cco/topology`) и туннелирование Tailscale Funnel.
- **`CCOBroadcastClient` (`src/sds/cco_broadcast_client.py`, `cco_tls_transport.py`):** Неблокирующий издатель по принципу «побеждает последний» (latest-wins), пересылающий обновления SDS на `/cco/broadcast` с аутентификацией `X-CCO-Token`, проверкой доверия ЦС TLS и опциональным пиннингом SHA-256 листового сертификата (`PinnedHTTPSConnection`).
- **`Безопасность Synapse gRPC` (`src/communication/grpc_security.py`):** Поддерживает TLS/mTLS (`CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_REQUIRE_CLIENT_CERT`) и `BearerTokenServerInterceptor` (`CARINA_GRPC_AUTH_TOKEN`) на порту `:50051`.
- **`Веб-приложение CCO` (`src_tsx/src_cco/`):** Интерфейс на React 18, TypeScript, Tailwind CSS с SVG-рендерером слоев карты и панелями Apache ECharts, использующий композитные CSS-анимации (`transform`/`opacity`), рефы панорамирования вьюпорта на `requestAnimationFrame`, неглубокое сравнение (shallow equality) модели представления и приостановку таймеров при `document.hidden`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
