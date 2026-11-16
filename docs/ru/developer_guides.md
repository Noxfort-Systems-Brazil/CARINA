---

tags: [developer, guide, setup, agents, config, 12-factor]

aliases: [Руководства разработчика, Справочник по настройке, Архитектура агентов]

---



# 🛠️ Руководства разработчика и интеграция



Данный документ представляет собой пошаговое руководство для инженеров-разработчиков по настройке рабочего окружения, конфигурированию параметров системы, созданию пользовательских агентов обучения с подкреплением и структуре кодовой базы CARINA.



⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🧪 См. [Тестирование и контроль качества](testing.md) | 🚀 См. [Развертывание и пакетирование](deployment_and_packaging.md) | 🗄️ См. [База данных и схемы](database_and_schemas.md) | 🚑 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md)



---



## 1. Развертывание окружения и конфигурация



CARINA следует методологии конфигурации приложений **12-Factor App**. Конфиденциальные секреты и параметры окружения отделены от рабочих гиперпараметров алгоритмов:



### 1.1 Секреты и инфраструктура: `.env`

Скопируйте файл примера в `.env`:

```bash

cp .env.example .env

```

Задайте ваши учетные данные:

```bash

CARINA_ENV=development                   # 'development' или 'production'

CARINA_DB_TYPE=sqlite                    # 'sqlite' или 'postgresql'

CARINA_DB_USER=admin

CARINA_DB_PASSWORD=admin

CARINA_DB_HOST=localhost

CARINA_DB_PORT=5432

CARINA_DB_NAME=carina_data

CARINA_DB_CONNECTED=False

CARINA_SNMP_COMMUNITY=public



# Аппаратный и веб-шлюз (Единый владелец CentralController: CARINA_GATEWAY_ROLE=owner; UI/AI: remote)

# В продакшене оставляйте CARINA_GATEWAY_ENABLED=False до задания токенов ниже!

CARINA_GATEWAY_ENABLED=False

CARINA_GATEWAY_PORT=2201

CARINA_TRAP_PORT=162

CARINA_EVP_AUTH_TOKEN=

CARINA_CCO_AUTH_TOKEN=

CARINA_CCO_ALLOWED_ORIGIN=

CARINA_GATEWAY_TLS_CERT=

CARINA_GATEWAY_TLS_KEY=

CARINA_GATEWAY_TLS_CA=

CARINA_GATEWAY_TLS_SERVER_NAME=

CARINA_TAILSCALE_AUTH_KEY=               # Опционально: tskey-auth-xxx для автоматической настройки Funnel



# Защита соединения Synapse HFT gRPC (:50051)

CARINA_GRPC_AUTH_TOKEN=

CARINA_GRPC_TLS_ENABLED=False

CARINA_GRPC_TLS_CERT=

CARINA_GRPC_TLS_KEY=

CARINA_GRPC_TLS_CA=

CARINA_GRPC_REQUIRE_CLIENT_CERT=False



# Опциональное переопределение каталогов хранения и конфигурации

CARINA_OUTPUT_DIR=

CARINA_CONFIG_DIR=



# Внешняя телеметрия Monitor (Брокер MQTT или URL HTTP/Cloud/Ngrok)

CARINA_MONITOR_ENABLED=False

CARINA_MQTT_HOST=localhost

CARINA_MQTT_PORT=1883

CARINA_MQTT_USER=

CARINA_MQTT_PASSWORD=

```



### 1.2 Эксплуатационные параметры: `config/settings.ini`

Гиперпараметры, интервалы обучения и допуски Watchdog настраиваются в файле [`config/settings.ini`](../../config/settings.ini):



```ini

[AI_TRAINING]

episode_max_steps = 100

telemetry_delta_ms = 250

update_timestep = 1024

gamma = 0.99

sequence_length = 12

k_epochs = 4

eps_clip = 0.2

gae_lambda = 0.95



[PBT]

evolution_frequency_episodes = 10

exploitation_percentile = 25

learning_rate_range = 0.00001, 0.0005



[MATURITY]

auto_pacing_enabled = True

auto_performance_margin_enabled = True

child_phase_episodes = 1344

teen_phase_min_episodes = 1344

performance_margin = 8.12



[REWARD_WEIGHTS]

auto_reward_weights_enabled = True

weight_waiting_time = -1.0

weight_flow = 6.04



[LOGGING]

log_step_progress = False

root_log_level = INFO

log_progress_frequency = 1

log_progress = True



[YELLOW_SCHEDULE]

yellow_schedule_enabled = False

yellow_schedule_start = 23:00

yellow_schedule_end = 05:00

yellow_schedule_all_semaphores = False



[WATCHDOG]

initial_grace_period_seconds = 10

heartbeat_timeout_seconds = 5.0



[GUARDIAN_AGENT]

learning_rate = 0.00025

gamma = 0.90

epsilon_start = 1.0

epsilon_end = 0.05

batch_size = 128



[HEATMAP_SCALING]

weight_occupancy = 1.0

weight_waiting_time = 1.5

weight_flow = -0.5

saturation_threshold = 100.0

lane_aggregation_strategy = max

heatmap_strategy = max

heatmap_saturation = 100.0



[REMOTE_GATEWAY]

gateway_enabled = False

cco_subdomain =

evp_subdomain =

evp_auth_token =

cco_auth_token =

cco_allowed_origin =

gateway_tls_cert =

gateway_tls_key =

cco_port = 8550

evp_port = 8085



[SYNAPSE]

port = 50051

max_workers = 10

grpc_auth_token =

grpc_tls_enabled = False

grpc_tls_cert =

grpc_tls_key =

grpc_tls_ca =

grpc_require_client_cert = False



[EVP]

auto_register_fleet = False

```



### 1.3 Взаимодействие с программными калькуляторами

Для автономной автокалибровки параметров сети CARINA предоставляет независимые модули расчетов в каталогах `src/promotion/` и `src/engine/`:



```python

# 1. Динамический пейсинг зрелости (длительность эпизодов по топологии):

from promotion.maturity_pacing_calculator import MaturityPacingCalculator

MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)



# 2. Динамическая маржа созревания (гидродинамика и скоростные режимы):

from promotion.performance_margin_calculator import PerformanceMarginCalculator

margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)

PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)



# 3. Физическая балансировка весов наград (время проезда по формулам HCM):

from engine.reward_weights_calculator import RewardWeightsCalculator

weights = RewardWeightsCalculator.calculate_from_topology(net, settings)

RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)

```



### 1.4 Работа с настройками (`src/settings/`)

CARINA реализует чистую архитектуру конфигурации по принципам SOLID в каталоге [`src/settings/`](../../src/settings).



Разработчики могут получать доступ к параметрам через модульный сервис `SettingsService` либо через фасад обратной совместимости `SettingsManager`:



```python

# Прямой модульный подход:

from settings import SettingsService, IniFileStorage, DotenvSecretProvider

service = SettingsService(

    storage=IniFileStorage("config/settings.ini"),

    env_provider=DotenvSecretProvider()

)

value = service.get("ai_gamma", default=0.99)



# Либо через фасад обратной совместимости (рекомендуется для существующего кода):

from utils.settings_manager import SettingsManager

settings_dict = SettingsManager().load_settings()

learning_rate = float(settings_dict.get("learning_rate", 0.00025))

```



Все ключи валидируются через [`SettingsSchema`](../../src/settings/schema.py), что гарантирует автоматическое сопоставление нужной секции INI и резервный поиск в переменных `.env`. Разделенные доменные контракты находятся в [`src/interfaces/`](../../src/interfaces) (`controller.py`, `drivers.py`, `engine.py`, `repositories.py`), а владение аппаратным шлюзом в подпроцессах регулируется переменной `CARINA_GATEWAY_ROLE` (`owner` в `CentralController` и `remote` в UI/AI/SDS).



---



## 2. Иерархия агентов и расширение обучения с подкреплением



Нейросетевая архитектура CARINA разделяет принятие решений на три специализированные роли в каталоге [`src/agents/`](../../src/agents):



1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)):** Тактический агент PPO-TCN, управляющий длительностью фаз конкретного перекрёстка.

2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)):** Нейро-символический страж D3QN, контролирующий безопасность и блокирующий опасные действия.

3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)):** Графовый координатор ST-GATv2 Lite, формирующий пространственно-временные контекстные векторы и «зелёные волны».



### 2.1 Реализация пользовательского агента

Для создания нового тактического агента (например, `CustomPPOAgent`):



1. Создайте файл `src/agents/custom_ppo_agent.py`:

```python

import torch

import torch.nn as nn



class CustomPPOAgent:

    def __init__(self, state_dim: int, action_dim: int, config: dict):

        self.state_dim = state_dim

        self.action_dim = action_dim

        self.config = config

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



    def act(self, observation_tensor: torch.Tensor, explore: bool = True) -> int:

        """Выбирает дискретное действие фазы светофора."""

        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):

            # Вычисление логитов действий

            action_index = 0

            return action_index



    def update(self, memory_buffer) -> dict:

        """Выполняет шаг оптимизации обратного распространения ошибки."""

        return {"loss": 0.0}

```



2. Зарегистрируйте ваш класс агента в [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py):

```python

from agents.custom_ppo_agent import CustomPPOAgent



# Внутри метода инициализации DecisionCoordinator:

if agent_type == "CUSTOM_PPO":

    self.agent = CustomPPOAgent(state_dim, action_dim, config)

```



---



## 3. Пакетирование и распространение



CARINA предоставляет скрипт многоэтапной герметичной сборки через Docker ([`scripts/build_deb.sh`](../../scripts/build_deb.sh)), который компилирует веб-интерфейс CCO (React), нативный исполняемый файл Go, изолирует виртуальное окружение Python и формирует полноценный пакет Debian (`dist/carina_1.0.0_amd64.deb`).



Для локальной сборки пакета:

```bash

./scripts/build_deb.sh

```



Инструкции по развертыванию сред и запуску служб приведены в руководстве [Развертывание и пакетирование](deployment_and_packaging.md).



---



## 4. Симуляция спецтранспорта и коридоров преемпции



Разработчики могут тестировать и валидировать подсистему приоритетного пропуска экстренных служб без реальных радиомаяков и выезда автомобилей с помощью встроенного симулятора CLI ([`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)):



### 4.1 Запуск режимов симуляции

```bash

# 1. Одиночный экстренный выезд (Скорая помощь SAMU мчится к перекрёстку с включенной сиреной):

python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0



# 2. Непрерывное патрулирование смешанного парка (Скорая, Пожарные, Полиция с телеметрией 2 Гц):

python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0



# 3. Подъезд с выключенной сиреной (Проверка отсутствия ложного срабатывания без сирены):

python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03

```



По умолчанию симулятор отправляет данные на `http://localhost:8085` (автономный приемник) или `http://localhost:2201` (веб-шлюз на Go). Назначение целевого адреса и порта:

```bash

python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency

```



### 4.2 Прямая подача пакетов через cURL

Разработчики также могут генерировать синтетические координаты GPS напрямую через утилиту cURL:

```bash

curl -X POST http://localhost:2201/api/v1/evp/telemetry \

  -H "Content-Type: application/json" \

  -d '{

    "vehicle_id": "SAMU-01",

    "corporation": "SAMU",

    "latitude": -23.55052,

    "longitude": -46.63330,

    "speed_kmh": 65.0,

    "heading_deg": 90.0,

    "siren_active": true,

    "timestamp": 1789458600.0

  }'

```

Ожидаемый ответ — `HTTP 204 No Content` ($< 1\text{ мс}$). Логи преемпции отображаются в консоли CARINA:

```text

[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)

[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01

[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}

```



---



<div align="center">

  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>

  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>

  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>

  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>

</div>
