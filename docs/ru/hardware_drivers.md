---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Драйверы оборудования, Полевые контроллеры, NTCIP 1202, Интеграция UTMC]
---

# 🚦 Драйверы оборудования и интеграция с физическими дорожными контроллерами

Данный документ описывает уровень интеграции CARINA с физическим периферийным оборудованием, расположенный в каталогах [`src/drivers/`](../../src/drivers) и [`src/controller/`](../../src/controller). В нем подробно рассматриваются протоколы связи (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), управление жизненным циклом соединений, сбор аппаратной телеметрии и детерминированный аварийный переход в безопасный режим (fail-safe).

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🏛️ См. [Архитектура мультипроцессинга](architecture.md) | 🛡️ См. [Безопасность и Watchdog](safety_and_watchdog.md) | 🚑 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md)

---

## 1. Архитектурный обзор

CARINA взаимодействует с реальными дорожными контроллерами светофорных объектов (включая Econolite, Siemens, Peek, SWARCO, Yunex) с помощью высокопроизводительного **аппаратного шлюза на Go** (`bin/carina-go`, компилируемого из каталога [`src_go/`](../../src_go)). Обмен данными между ядром CARINA на Python и шлюзом на Go осуществляется строго через **стандартные системные пайпы ОС (`stdin`/`stdout`)** с использованием потока структурированных строк JSON (Line-Delimited JSON / NDJSON). Это гарантирует **полное отсутствие локальных портов IPC, открываемых на хост-машине**, субмиллисекундное время отклика и стопроцентное исключение влияния блокировок GIL Python.

### 1.1 Единое владение шлюзом (`CARINA_GATEWAY_ROLE`) и замкнутая архитектура
Для предотвращения дублирования процессов `bin/carina-go`, конфликтов на порту UDP `162` слушателя трапов и расщепления состояния SNMP:
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`):** Монопольно запускает `bin/carina-go`, размещает [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (в составе `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` и `TailscaleGatewayAdapter`), владеет локальными SNMP-соединениями `HardwareConnectionManager` и транслирует снимки состояния подчиненным воркерам.
- **`AI_Process`, `SDS` и `UI` (`CARINA_GATEWAY_ROLE=remote`):** Работают как удаленные зеркала без запуска локальных бинарников Go и без привязки к UDP `162`. [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py) (материализуемый через [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py)) перенаправляет команды (`ai_hardware_cmd`) и преемпции EVP (`ai_evp_preempt`) обратно в `CentralController` через [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Декодирование замкнутой телеметрии:** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) и [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) преобразуют реальные битовые маски контроллеров (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) в 0-индексированные стадии SUMO для извлечения состояния ИИ и согласования передачи управления F.E.N.I.X.

В дополнение к стандартному управлению по NTCIP/UTMC, шлюз на Go включает **диспетчер преемпции EVP** (`src_go/evp_go/dispatcher.go`) для микросекундного удержания зеленой фазы и **удаленный веб-шлюз** (`src_go/web_gateway/server.go`), обеспечивающий защищенную токенами связанность через Tailscale Mesh, терминацию TLS, прием телеметрии по HTTP (порт `2201`) и потоковую передачу Server-Sent Events (SSE) для видеостен CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │      CentralController (CARINA_GATEWAY_ROLE=owner)     │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │ (Статусы и SNMPv2/v3)│   │   │ (Сторожевой таймер)  │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │(Диспетчеризация EVP) │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Подпроцесс пайпов ОС)  │
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - Ноль локальных портов управления)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │            АППАРАТНЫЙ ШЛЮЗ CARINA (Бинарник Go)           │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │    Драйвер NTCIP   │         │    Драйвер UTMC    │   │
      │   │  (NTCIP 1202 v02)  │         │(Стандарт UK UTMC2) │   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │  Диспетчер EVP   │ │GoSNMPv2/3│ │ Бинар. дек. трапов│  │
      │  │(Прямой OID Hold) │ │UDP Пт 161│ │ (SNMPv1/v2c/v3)  │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Удаленный прием и сеть Mesh
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │       Веб-шлюз и сеть Tailscale Mesh (Порт 2201 / TLS)    │
      │  - Fail-closed по умолчанию (HTTP 503 при отключении)     │
      │  - POST /api/v1/evp/telemetry (Токен-аутент., HTTP 204)   │
      │  - GET /cco/stream (Токен-аутент., CORS, SSE Видеостена)  │
      │  - Tailscale Funnel / Зашифрованная одноранговая сеть     │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. Драйвер контроллеров NTCIP 1202 Actuated Signal Controller (ASC)

**Стандарт NTCIP 1202** (National Transportation Communications for ITS Protocol) является доминирующим промышленным стандартом в Северной Америке и широко применяется в современных проектах ИТС по всему миру.

### 2.1 Файловая архитектура
**Реализация шлюза на Go (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go): Нативный оркестратор драйвера NTCIP на Go.
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go): Опрос телеметрии активных фаз, состояния колец регулирования и сработок детекторов транспорта.
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go): Движок удержания фаз (hold), принудительного завершения (force-off) и вызова фаз (call).
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go): Преобразует дискретные действия CARINA в битовые маски фаз NTCIP.
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) и [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json): Встроенные профили определений идентификаторов объектов OID.

**Слой моста и прокси на Python (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py): Клиент IPC по анонимным пайпам NDJSON, управляющий подпроцессом `bin/carina-go`.
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py): Полный прокси `BaseTrafficDriver`, перенаправляющий команды демону на Go.
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py): Создает экземпляры прокси драйверов на основе автоопределения марки и модели контроллера.

### 2.2 Таблица стандартных сопоставлений OID (`src_go/configs/ntcip_oids.json`)

Все OID статуса (`phaseStatusGroup`) и управления (`phaseControlGroup`) стандарта NTCIP 1202 поддерживают как целочисленные PDU, так и `OCTET STRING`/`BitString` через [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go), и могут переопределяться индивидуально для перекрёстка через `config_path`:

| Ключ объекта | ASN.1 OID | Группа / Тип | Описание |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | Статус / Битовая маска | Битовая маска фаз, находящихся в красном сигнале. |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | Статус / Битовая маска | Битовая маска фаз, находящихся в желтом сигнале. |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | Статус / Битовая маска | Битовая маска фаз, находящихся в зеленом сигнале. |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | Статус / Битовая маска | Активные вызовы детекторов транспорта, сообщаемые контроллером. |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | Статус / Битовая маска | Активные вызовы пешеходных кнопок, сообщаемые контроллером. |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | Управление / Битовая маска | Исключает указанные фазы из обслуживания. |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | Управление / Битовая маска | Удерживает активный зеленый сигнал (`ascPhaseControlHold`). |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | Управление / Битовая маска | Принудительно завершает текущую зеленую фазу (`ascPhaseControlForceOff`). |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | Управление / Битовая маска | Подает синтетический вызов от детектора транспорта (`ascPhaseControlVehCall`). |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | Управление / Битовая маска | Подает синтетический пешеходный вызов (`ascPhaseControlPedCall`). |

---

## 3. Драйвер UTMC / UTMC2 и поддержка SNMPv3 USM

Для перекрёстков, функционирующих под управлением британского стандарта **Urban Traffic Management and Control (UTMC)** или аутентифицированных шкафов контроллеров **SNMPv3**:

### 3.1 Файловая архитектура
**Реализация шлюза на Go (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Нативный обработчик протокола связи UTMC на Go с потокобезопасными методами `Probe()` и `CloseTransport()`.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Парсер подтверждения стадий (`status_active`, `status_leaving`, `status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`, `status_ped_demand`).
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Исполнение запросов стадий, удержания, принудительного завершения и безопасных по межзеленым интервалам логических действий.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Сопоставляет стадии UTMC (Stage 1..8) действиям нейросети CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) и [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Встроенные профили OID стандарта UTMC.
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go): **Движок SNMPv3 USM**, поддерживающий `NoAuthNoPriv`, `AuthNoPriv` и `AuthPriv` с протоколами аутентификации (`MD5`, `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512`) и шифрования (`DES`, `AES`, `AES192`, `AES256`, `AES192C`, `AES256C`). JSON-метаданные `snmp_config` и переопределения OID `config_path` для каждого перекрёстка передаются от [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) и [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) через [`DriverFactory`](../../src/drivers/driver_factory.py) в `GoGatewayClient`.

---

## 4. Аппаратный диспетчер преемпции EVP (`src_go/evp_go/`)

**Диспетчер преемпции EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) обрабатывает запросы на формирование «зелёных коридоров» спецтранспорта в реальном времени с субмиллисекундным воздействием на контроллер:

- **Обход цикла инференса:** Сигналы приоритета обходят стандартные вычисления нейросети и межперекрёстную координацию, напрямую активируя удержание зеленого сигнала нужного направления.
- **Прямая запись OID SNMP Hold:** Преобразует индексы зеленых фаз (`stage_idx` и `stage_codes`) в битовые маски NTCIP `phase_control.hold` (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) или битовые маски удержания стадий UTMC, надежно удерживая конфликтующие направления на красном сигнале при предоставлении беспрепятственного проезда.
- **Микросекундный протокол IPC:** Активируется командой `evp_preempt` формата NDJSON через системные пайпы:
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **Сторожевой таймер и освобождение фазы:** Удержание фазы снимается либо при пересечении машиной порога выезда ($\le 15\text{ м}$), либо по истечении максимального защитного интервала ($45\text{ с}$). В случае сбоя или разрыва связи со шлюзом контроллер аппаратно снимает удержание после 3 пропущенных сигналов heartbeat.

---

## 5. Удаленный веб-шлюз и ячеистые сети Mesh (`src_go/web_gateway/`)

Для распределенных инфраструктур «Умного города», где автомобили экстренных служб или операторы ЦОДД требуют защищенного удаленного доступа без открытых белых IP:

- **Шифрованная сеть Tailscale Mesh:** Интегрирована через [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go), позволяя периферийным контроллерам CARINA объединяться в сквозную шифрованную оверлейную сеть Zero-Trust.
- **Туннель Tailscale Funnel (Порт 2201):** Публично открывает высокопроизводительные эндпоинты по протоколу TLS без проброса портов на межсетевых экранах.
- **Высокоскоростной прием телеметрии:** Предоставляет маршрут `POST /api/v1/evp/telemetry` (HTTP 204 fire-and-forget) для приема высокочастотных GPS-пакетов бортовых маяков с субмиллисекундным временем ответа.
- **Хаб рассылки Server-Sent Events (SSE):** Модуль [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) непрерывно транслирует телеметрию перекрёстков, траектории спецтранспорта и состояния светофоров на видеостены операторов CCO через `GET /cco/stream`.

---

## 6. Управление оборудованием и отказоустойчивость (Fail-Safe)

### 6.1 Жизненный цикл соединений и пулы (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) и [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py): Управляют конечными автоматами соединений (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`), пассивными зеркальными представлениями в режиме `remote` (`update_remote_hardware_status`), автоопределением портов симулятора ([`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)) и массовым восстановлением из CSV ([`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)).
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) и [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py): Сохраняют IP-адреса и опциональный JSON `snmp_config` (SNMPv3 USM / пользовательский `config_path` OID) в таблице `hardware_controller_connections` и CSV-шаблонах, сохраняя [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) как фасад обратной совместимости.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Выполняет аварийный возврат через `HardwareGatewayCoordinator.on_failsafe_triggered()` и восстановление через `on_failsafe_recovered()`.

### 6.2 Детерминизм безаварийного режима (Fail-Safe), восстановление и бинарные SNMP-трапы
1. **Потеря сигнала Heartbeat и обратимый Fail-Safe:** Если связь с активным контроллером обрывается или срабатывает fail-safe Watchdog, `EmergencyReleaseControlAll()` приостанавливает heartbeat-сигналы и снимает удержания фаз, сохраняя SNMP-драйверы и слушатель трапов активными, чтобы команда `resume_control` (`ResumeControlAll()`) могла плавно возобновить работу при восстановлении. При выходе из процесса или `EOF`/`SIGPIPE` функция `ShutdownAll()` окончательно снимает удержания и закрывает сокеты.
2. **Межзеленая защита (`HardwareStageActuator`):** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) пропускает конфликтующие вызовы `send_stage_hold` во время межзеленых интервалов желтого/всекрасного (`_is_intergreen_stage`) и единообразно разрешает идентификаторы с префиксом `tl_`.
3. **Бинарный декодер SNMPv1/v2c/v3 трапов (`src_go/pkg/traplistener/snmp_decoder.go`):** Разбирает бинарные пакеты Trap/Inform в кодировке ASN.1 BER на UDP-порту `162` (`CARINA_TRAP_PORT`), классифицируя тревоги `coldStart`, `warmStart`, `linkDown`, `linkUp`, `authenticationFailure`, NTCIP (`.1206.*`) и UTMC (`.13267.*`, `.2825.*`) по критичности (`CRITICAL`, `WARNING`, `INFO`).
4. **Контроль конфликтов сигналов:** Все исходящие команды валидируются модулем [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) перед отправкой, проверяющим матрицы конфликтов и нормативное время очистки перекрёстка.

### 6.3 Оповещение об аппаратных инцидентах и дедупликация (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py): Перехватывает смену аппаратных статусов (`CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`) и формирует стандартизированные JSON-сообщения инцидентов.
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py): Предотвращает штормы оповещений, сохраняя хэши активных инцидентов с фильтрацией дребезга в `.carina_incident_filter_cache.json`.
- Отправляет алерты через `MonitorClient` по настроенному транспорту телеметрии (локальный брокер MQTT или облачный эндпоинт HTTP/Ngrok).

---

## 7. Безопасность и учетные данные контроллеров

Учетные данные оборудования никогда не должны жестко прописываться в кодовой базе. CARINA считывает пароли SNMP и параметры авторизации через переменные окружения, определенные в [`.env`](../../.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

Конфигурацию политик безопасности и роли пользователей см. в [Безопасность и аутентификация](security_and_auth.md).
Схемы сериализации телеметрии см. в [Справочник API](api_reference.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
