---

tags: [developer, guide, setup, agents, config, 12-factor]

aliases: [开发者指南, 配置参考规范, 智能体架构]

---



# 🛠️ 开发者指南与系统集成规范



本文档为开发人员与系统集成工程师提供循序渐进的工程指南，涵盖开发环境配置、系统参数调优、自定义强化学习智能体开发以及 CARINA 核心源码库的架构理解。



⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🧪 查阅 [测试规范与质量保证](testing.md) | 🚀 查阅 [部署与打包发布](deployment_and_packaging.md) | 🗄️ 查阅 [数据库与关系模式](database_and_schemas.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)



---



## 1. 开发环境初始化与配置管理



CARINA 严格遵循 **12-Factor App** 配置方法论。将涉及安全凭据的环境配置与业务层运行超参数彻底剥离：



### 1.1 基础设施机密配置：`.env`

复制模板文件并生成 `.env`：

```bash

cp .env.example .env

```

配置开发或生产环境凭据：

```bash

CARINA_ENV=development                   # 'development' 或 'production'

CARINA_DB_TYPE=sqlite                    # 'sqlite' 或 'postgresql'

CARINA_DB_USER=admin

CARINA_DB_PASSWORD=admin

CARINA_DB_HOST=localhost

CARINA_DB_PORT=5432

CARINA_DB_NAME=carina_data

CARINA_DB_CONNECTED=False

CARINA_SNMP_COMMUNITY=public



# 现场硬件与 Web 网关 (单一所有者 CentralController: CARINA_GATEWAY_ROLE=owner; UI/AI: remote)

# 在设置以下认证令牌之前，生产环境请保持 CARINA_GATEWAY_ENABLED=False！

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

CARINA_TAILSCALE_AUTH_KEY=               # 可选: 用于自动配置 Funnel 的 tskey-auth-xxx



# Synapse HFT gRPC 链路安全 (:50051)

CARINA_GRPC_AUTH_TOKEN=

CARINA_GRPC_TLS_ENABLED=False

CARINA_GRPC_TLS_CERT=

CARINA_GRPC_TLS_KEY=

CARINA_GRPC_TLS_CA=

CARINA_GRPC_REQUIRE_CLIENT_CERT=False



# 可选存储 / 配置目录覆盖

CARINA_OUTPUT_DIR=

CARINA_CONFIG_DIR=



# 外部监控遥测平台 (MQTT Broker 或 HTTP/Cloud/Ngrok URL)

CARINA_MONITOR_ENABLED=False

CARINA_MQTT_HOST=localhost

CARINA_MQTT_PORT=1883

CARINA_MQTT_USER=

CARINA_MQTT_PASSWORD=

```



### 1.2 运行时业务参数：`config/settings.ini`

深度强化学习超参数、训练迭代周期以及看门狗容错阈值位于 [`config/settings.ini`](../../config/settings.ini)：



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



### 1.3 与自动化物理计算器交互

针对路网自适应校准，CARINA 在 `src/promotion/` 与 `src/engine/` 暴露了独立计算工具：



```python

# 1. 动态成熟度节奏调优 (依据路网物理规模自动计算回合跨度):

from promotion.maturity_pacing_calculator import MaturityPacingCalculator

MaturityPacingCalculator.apply_if_enabled(maturity_manager, net, tls_list, settings)



# 2. 动态毕业性能增益裕度计算 (基于流体动力学与限速):

from promotion.performance_margin_calculator import PerformanceMarginCalculator

margin = PerformanceMarginCalculator.calculate_from_topology(net, settings)

PerformanceMarginCalculator.apply_if_enabled(maturity_manager, margin, settings)



# 3. 动态物理奖励权重平衡 (基于 HCM 路段行程时间):

from engine.reward_weights_calculator import RewardWeightsCalculator

weights = RewardWeightsCalculator.calculate_from_topology(net, settings)

RewardWeightsCalculator.apply_if_enabled(reward_calculator, weights, settings)

```



### 1.4 配置服务调用规范 (`src/settings/`)

CARINA 在 [`src/settings/`](../../src/settings) 提供了遵循 SOLID 原则的配置子系统。



开发者可通过模块化 `SettingsService` 或向后兼容的 `SettingsManager` 门面读取配置：



```python

# 推荐的模块化方式:

from settings import SettingsService, IniFileStorage, DotenvSecretProvider

service = SettingsService(

    storage=IniFileStorage("config/settings.ini"),

    env_provider=DotenvSecretProvider()

)

value = service.get("ai_gamma", default=0.99)



# 或通过向后兼容门面 (旧有代码库推荐):

from utils.settings_manager import SettingsManager

settings_dict = SettingsManager().load_settings()

learning_rate = float(settings_dict.get("learning_rate", 0.00025))

```



所有配置键均通过 [`SettingsSchema`](../../src/settings/schema.py) 进行强校验，确保自动映射至正确的 INI 配置段及 `.env` 备用回退。隔离的领域契约接口位于 [`src/interfaces/`](../../src/interfaces)（`controller.py`、`drivers.py`、`engine.py`、`repositories.py`），而子进程硬件所有权则由 `CARINA_GATEWAY_ROLE` 严格治理（`CentralController` 为 `owner`，UI/AI/SDS 为 `remote`）。



---



## 2. 智能体层级架构与强化学习算法扩展



CARINA 的神经网络架构将控制决策解耦为 [`src/agents/`](../../src/agents) 下的三个专业角色：



1. **`LocalAgent` ([`local_agent.py`](../../src/agents/local_agent.py)):** 战术级 PPO-TCN 智能体，直接决定本交叉口的信号放行相位与持续时长。

2. **`GuardianAgent` ([`guardian_agent.py`](../../src/agents/guardian_agent.py)):** 神经符号 D3QN 安全守卫，实时审计并否决存在溢流锁死隐患的不安全动作。

3. **`StrategistAgent` ([`strategist_agent.py`](../../src/agents/strategist_agent.py)):** ST-GATv2 Lite 宏观拓扑图协调器，负责提取路网时空嵌入并促成干线绿波协同涌现。



### 2.1 扩展实现自定义智能体

以构建新型战术智能体（如 `CustomPPOAgent`）为例：



1. 创建 `src/agents/custom_ppo_agent.py`：

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

        """根据当前路况观测张量选择离散交通信号相位动作。"""

        with torch.amp.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu"):

            # 计算动作 Logits 分布

            action_index = 0

            return action_index



    def update(self, memory_buffer) -> dict:

        """执行梯度反向传播策略优化。"""

        return {"loss": 0.0}

```



2. 在 [`src/core/decision_coordinator.py`](../../src/core/decision_coordinator.py) 中注册智能体：

```python

from agents.custom_ppo_agent import CustomPPOAgent



# 在 DecisionCoordinator 初始化逻辑中:

if agent_type == "CUSTOM_PPO":

    self.agent = CustomPPOAgent(state_dim, action_dim, config)

```



---



## 3. 打包发布与分发体系



CARINA 提供了全自动多阶段 Docker 密封式构建脚本 ([`scripts/build_deb.sh`](../../scripts/build_deb.sh))，可同时编译 React CCO 前端、原生构建 Go 语言网关二进制文件、准备隔离的 Python 运行环境并打包为自包含的 Debian 安装包 (`dist/carina_1.0.0_amd64.deb`)。



本地编译安装包：

```bash

./scripts/build_deb.sh

```



有关安装与系统部署细节，请参阅 [部署与打包发布](deployment_and_packaging.md)。



---



## 4. 特勤应急车辆与绿波生命走廊仿真调试



开发人员可以使用内置的仿真 CLI 命令行工具（[`demo/evp_vehicle_simulator.py`](../../demo/evp_vehicle_simulator.py)），在完全无需物理车载信标或现场救护车配合的情况下，快速验证 EVP 绿波走廊功能：



### 4.1 运行内置仿真场景

```bash

# 1. 单车极速出警演练 (SAMU 急救车鸣警向目标路口高速行驶):

python demo/evp_vehicle_simulator.py --mode emergency --vehicle SAMU-01 --duration 25.0



# 2. 全城特勤车队联合巡逻演练 (急救车、消防车、警车以 2 Hz 频率绕城上报):

python demo/evp_vehicle_simulator.py --mode patrol --duration 60.0



# 3. 警报未开启测试 (验证特勤车辆在关闭听觉警报器时的优先否决逻辑):

python demo/evp_vehicle_simulator.py --mode siren_off --vehicle BOMB-03

```



默认情况下，仿真器将数据上报至 `http://localhost:8085`（独立 Python 接收器）或 `http://localhost:2201`（Go Web 网关）。可通过参数指定目标端点：

```bash

python demo/evp_vehicle_simulator.py --host 127.0.0.1 --port 2201 --mode emergency

```



### 4.2 基于 cURL 直接模拟 HTTP 遥测注入

开发者还可以直接通过命令行触发合成 GPS 定位遥测：

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

预期响应为瞬时返回的 `HTTP 204 No Content`（耗时 $< 1\text{ ms}$）。可在 CARINA 控制台实时观察优先控制日志流：

```text

[EVPKinematicsEngine] Vehicle SAMU-01 entered approach gate (112.4m to J01)

[EVPPreemptionEngine] Granting emergency preemption hold on Stage 1 for SAMU-01

[GoGatewayClient] Sent NDJSON command: {"cmd":"evp_preempt","intersection_id":"J01",...}

```



---



<div align="center">

  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>

  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>

  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>

  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>

</div>
