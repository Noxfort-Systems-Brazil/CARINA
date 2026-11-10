---
tags: [api, grpc, ipc, reference, protobuf]
aliases: [Справочник API, Synapse HFT, Очереди IPC, Интерфейс gRPC]
---

# ⚡ Справочник API и спецификации протокола Synapse HFT

Данный документ представляет собой нормативную спецификацию интерфейсов CARINA. В нем рассматриваются **протокол gRPC Synapse HFT**, **метрики экспортера Prometheus** и **схемы межпроцессного взаимодействия (IPC)**.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🚨 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md) | 🚦 См. [Драйверы оборудования](hardware_drivers.md) | 🛡️ См. [Безопасность и Watchdog](safety_and_watchdog.md) | 🗄️ См. [База данных и схемы](database_and_schemas.md)

---

## 1. Определение сервиса gRPC Synapse HFT (`proto/synapse_hft.proto`)

CARINA взаимодействует с внешними датчиками, контроллерами светофорных объектов и средами микроскопического моделирования движения (SUMO/CityFlow) через высокочастотный **протокол Synapse HFT** поверх gRPC.

- **Порт по умолчанию:** `50051` (настраивается в `config/settings.ini`)
- **Транспорт:** HTTP/2 поверх TCP с опциональным шифрованием TLS.
- **Пакет Protobuf:** `synapse.hft`

```protobuf
syntax = "proto3";
package synapse.hft;

service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

### 1.1 Описание методов RPC

#### `Ping`
- **Запрос:** `Empty`
- **Ответ:** `SystemState` (возвращает статус сервера, булевый флаг активности и метку времени эпохи UTC `server_time`).
- **Целевая задержка:** $< 1\text{ мс}$

#### `LoadScenario`
- **Запрос:** `ScenarioDefinition` (передает сжатую геометрию сети `.net.xml.gz`, узлы/ребра топологии и JSON суточных графиков пиковых нагрузок от классификатора ADAGIO).
- **Ответ:** `ScenarioStatus` (булевый флаг `accepted` и текстовое сообщение о статусе).

#### `SystemControl`
- **Запрос:** `ControlCommand` (команда из перечисления: `START`, `PAUSE`, `STOP`, `RESET`).
- **Ответ:** `CommandResponse` (булевый флаг `success` и строка `new_state`).

#### `StreamTraffic`
- **Запрос:** `stream TrafficFrame` (высокочастотный поток данных о загрузке полос, скоростях транспорта, длине очередей и плотности потока).
- **Ответ:** `SystemState`

---

## 2. Схемы сообщений телеметрии и управления

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // Коэффициент занятости полосы [0.0 - 1.0]
  float mean_speed = 2;     // Пространственно-средняя скорость в м/с
  int32 queue_length = 3;   // Количество остановившихся автомобилей в очереди
  float density = 4;        // Плотность потока (авт/км)
}
```

### 2.2 `ScenarioDefinition`
```protobuf
message ScenarioDefinition {
  string map_hash = 1;
  TopologyGraph graph = 2;
  MapGeometry geometry = 3;
  bytes map_file_content = 4;
  string map_file_name = 5;
  string peak_schedule_json = 6;
}
```

---

## 3. Спецификации очередей межпроцессного взаимодействия (IPC)

CARINA координирует 11 буферизованных очередей IPC и 1 дуплексный канал связи (Pipe), управляемые модулем [`ProcessManager`](../../src/launcher/process_manager.py):

| Имя очереди | Макс. размер | Процесс-производитель | Процесс-потребитель | Схема полезной нагрузки / Тип сообщения |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Pipe | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Pipe | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | Все микросервисы | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Исторические метрики потока для агрегации в PostgreSQL |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | Команды GUI, ручное вмешательство, тайминги и настройки |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | Бессетевые пакеты телеметрии в ОЗУ, заторы и метрики зрелости |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `InfrastructureClient` | Инженерные отчеты обоснований и рекомендации по фазированию |
| **`mfd_trigger`** | 10 | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

Спецификации управления контроллерами по NTCIP и UTMC см. в руководстве [Драйверы оборудования](hardware_drivers.md).

---

## 4. Метрики экспортера Prometheus

Компонент `MetricsManager` отдает эксплуатационную телеметрию реального времени по **протоколу HTTP на порту 8001** (маршрут `/metrics`).

```text
# Сводка метрик Prometheus:
carina_step_latency_seconds_bucket{le="0.005"}   # Гистограмма задержки от приема телеметрии до выдачи действия
carina_ppo_reward_total                          # Суммарное вознаграждение тактического агента PPO
carina_guardian_veto_total{type="symbolic"}      # Счетчик символических вето безопасности
carina_guardian_veto_total{type="neural"}        # Счетчик нейросетевых вето заторов PAE
carina_mfd_network_density_veh_km               # Макроскопическая плотность транспортной сети
carina_mfd_network_flow_veh_hr                   # Макроскопическая пропускная способность сети
carina_active_processes_count                    # Количество активных фоновых микросервисов
```

---

## 5. Внешний мониторинг телеметрии и протоколы передачи (`src/transports/`)

CARINA передает статусные сигналы пульса (heartbeat) и аппаратные тревоги во внешние диспетчерские системы и облачные платформы аналитики через [`MonitorClient`](../../src/communication/monitor_client.py) и [`src/transports/`](../../src/transports).

### 5.1 Форматы полезной нагрузки телеметрии

#### Пакет аппаратного инцидента (`noxfort/incidents/` или HTTP POST)
```json
{
  "intersection_id": "cruzamento_av_jk_01",
  "level": "CRITICAL",
  "category": "HARDWARE_DISCONNECT",
  "message": "[FailsafeManager] Controller dropped connection. Reverting to fixed-time.",
  "occurred_at": "2026-09-15T01:30:00Z",
  "is_active": true
}
```

#### Пакет телеметрии пульса системы (`noxfort/telemetry/` или HTTP POST)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

### 5.2 Протоколы транспорта

| Протокол | Пример конфигурации (`CARINA_MQTT_HOST`) | Реализация | Характеристики |
| :--- | :--- | :--- | :--- |
| **Брокер MQTT** | `127.0.0.1:1883` или `broker.emqx.io` | [`MonitorMqttTransport`](../../src/transports/mqtt_transport.py) | Paho MQTT v2, keepalive 60 с, топики `noxfort/telemetry/` и `noxfort/incidents/`. |
| **HTTP / HTTPS REST** | `https://monitor.noxfort.com/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | JSON `POST`, постоянная сессия `requests.Session`, экспоненциальный retry, таймаут 3.0 с. |
| **Облачные туннели (Ngrok)** | `https://xxxx.ngrok-free.dev/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | Автоопределение через `endpoint_resolver.py` с маршрутизацией через защищенный HTTPS-туннель. |

### 5.3 Правила классификации конечных точек
Фабричная функция [`create_monitor_transport()`](../../src/transports/factory.py) автоматически выбирает требуемый транспорт:
1. Если строка хоста начинается с `http://` или `https://` $\implies$ **HTTP Transport**.
2. Если строка содержит `.ngrok`, `.run.app` или путь `/api/` $\implies$ **HTTP Transport** (автоматически добавляет префикс `https://`, если схема протокола была опущена).
3. Если строка содержит IP-адрес или домен с опциональным портом (например, `10.0.0.1:1883`) $\implies$ **MQTT Transport**.

---

## 6. HTTP API приема телеметрии спецтранспорта

Скомпилированный веб-шлюз на Go предоставляет высокопроизводительный однонаправленный (fire-and-forget) маршрут приема данных бортовых GPS-маяков экстренных служб:

- **Эндпоинт:** `POST /api/v1/evp/telemetry` (псевдонимы: `POST /amb` или `POST /amb/`)
- **Порт:** `2201` (веб-шлюз Go / Tailscale Funnel) или `8085` (выделенный сервер Go EVP [`src_go/evp_go/`](../../src_go/evp_go) / автономный приемник)
- **Ответ:** `204 No Content` (мгновенный возврат с субмиллисекундной обработкой)
- **Схема полезной нагрузки:**
  ```json
  {
    "vehicle_id": "SAMU-01",
    "corporation": "SAMU",
    "latitude": -23.31028,
    "longitude": -51.16278,
    "speed_kmh": 65.4,
    "heading_deg": 180.0,
    "siren_active": true,
    "timestamp": 1789458600.0
  }
  ```

---

## 7. Набор команд NDJSON IPC аппаратного и веб-шлюза на Go

Команды, отправляемые из ядра Python системы CARINA демону `bin/carina-go` через стандартные анонимные системные пайпы (`stdin`/`stdout`):

| Команда (`cmd`) | Параметры / Полезная нагрузка | Возвращаемые данные | Описание |
| :--- | :--- | :--- | :--- |
| **`ping`** | Нет | `"pong"` | Проверка работоспособности шлюза ($< 1\text{ мс}$). |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `protocol`, `green_stages` | Метаданные соединения | Устанавливает сессию связи SNMP/UDP с полевым контроллером. |
| **`disconnect`** | `intersection_id` | `success: true` | Закрывает соединение и освобождает сетевой сокет. |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | Передает нейросетевое или защитное действие физическим фазовым группам. |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `vehicle_id` | Строка выполненного действия | Передает микросекундную команду преемпции фазы контроллеру. |
| **`cco_broadcast`** | `data: dict` | `success: true` | Транслирует кадры телеметрии подключенным клиентам CCO SSE без ожидания ответа. |
| **`tailscale_status`** | Нет | `TailscaleStatus` JSON | Запрашивает домен Tailscale Funnel, состояние узла и публичные URL CCO. |
| **`emergency_release`** | Нет | `success: true` | Безусловно сбрасывает все удержания фаз по всей городской сети. |

---

## 8. Конечные точки REST и SSE оператора центра управления (CCO)

Доступны на порту `2201` веб-шлюза Go (и защищены шифрованием Tailscale Funnel):

- **`GET /health`**: Возвращает статус состояния системы и доступность шлюза.
- **`GET /cco` и `GET /cco/`**: Отдает собранное веб-приложение интерфейса оператора CCO на React 18.
- **`GET /cco/stream`**: Постоянный поток Server-Sent Events (SSE), транслирующий состояния светофоров, теплокарты плотности и координаты спецтранспорта на видеостены ЦОДД в реальном времени.
- **`GET /cco/topology`**: Отдает векторную геометрию улично-дорожной сети в формате GeoJSON/JSON, схемы полос и координаты перекрёстков для рендеринга интерактивных карт.

---

## 9. Утилитарные модули темпорального пейсинга, созревания и недельного покрытия

Интерфейсы Python ядра CARINA для временного регулирования и контроля прогресса созревания:

### 9.1 `EpisodeStepCalculator` (`src.utils.episode_step_calculator`)
Динамически вычисляет количество шагов в эпизоде на основе топологии дорожной сети:
- **`calculate(net_or_path: Union[str, Any], telemetry_delta_ms: float = 250.0) -> EpisodePacingResult`**
  Парсит дорожную сеть SUMO, объединяет встречные направления улиц, исключает внутренние соединители перекрестков (`:`), рассчитывает топологическую сложность $C_{\text{topo}}$, сублинейное время физической релаксации $T_{\text{physical}}$ и возвращает `EpisodePacingResult` с `episode_steps`, `duration_seconds` и недельными минимумами эпизодов (`child_episodes_1_week`, `teen_episodes_1_week`).

### 9.2 `WeeklyCoverageTracker` (`src.core.weekly_coverage_tracker`)
Отслеживает наблюдение на протяжении всех 168 часов реального астрономического календаря ($7\text{ дней} \times 24\text{ часа}$) с атомарным сохранением:
- **`register_step(raw_timestamp: float) -> Tuple[int, int]`**: Фиксирует телеметрические фреймы в матрице `(день_недели, час)` по реальным UNIX-таймстемпам.
- **`is_week_completed() -> bool`**: Возвращает `True`, если покрыты все 168 часовых интервалов недели.
- **`get_completion_ratio() -> float`**: Возвращает текущую долю покрытия недели в диапазоне $[0.0, 1.0]$.
- **`save_state() / load_state()`**: Атомарно сохраняет и восстанавливает прогресс на диске (`weekly_coverage_{phase}.json`), выдерживая паузы и перезапуски процессов.

### 9.3 `ActionAuthorizer` (`src.core.action_authorizer`)
Авторизует физическое управление аппаратным обеспечением в зависимости от стадии зрелости и астрономического календаря:
- **`is_action_authorized(agent_id: str, maturity: Maturity, sim_time: float, raw_timestamp: float = 0.0) -> Tuple[bool, str]`**: Проверяет право агента воздействовать на контроллеры. Ограничивает агентов `TEEN` исключительно внепиковыми интервалами, принудительно переводя в теневой режим в классические часы пик (06:30-09:00 и 17:00-19:30 по будням) или по динамическому расписанию Synapse.
- **`load_peak_schedule_json(schedule_data: dict) -> None`**: Загружает динамическое расписание пиковых периодов, переданное модулем Synapse.

### 9.4 `MaturityPacingCalculator` (`src.promotion.maturity_pacing_calculator`)
- **`calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]`**: Возвращает `(child_episodes, teen_episodes, child_steps, teen_steps)` с соблюдением неприкосновенного недельного минимума ($E_{\text{week}} \times S \times \Delta t \ge 604\,800\text{ с}$).
- **`apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool`**: Автоматически передает рассчитанные динамические параметры в `MaturityManager`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
