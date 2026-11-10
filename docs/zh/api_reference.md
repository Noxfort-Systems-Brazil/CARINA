---
tags: [api, grpc, ipc, reference, protobuf]
aliases: [API参考规范, Synapse HFT, IPC队列, gRPC接口]
---

# ⚡ API 接口参考与 Synapse HFT 协议规范

本文档为 CARINA 系统的权威接口规范标准。涵盖 **Synapse HFT gRPC 协议**、**Prometheus 指标导出器**以及**进程间通信 (IPC) 队列模式**。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🚨 查阅 [EVP 优先通行](evp_and_preemption.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🗄️ 查阅 [数据库与关系模式](database_and_schemas.md)

---

## 1. Synapse HFT gRPC 服务定义 (`proto/synapse_hft.proto`)

CARINA 通过基于 gRPC 的 **Synapse HFT 协议**与外部传感器、现场交通信号机以及微观交通仿真环境（SUMO / CityFlow）实现低延迟交互。

- **默认监听端口：** `50051`（可于 `config/settings.ini` 动态配置）
- **底层传输协议：** 基于 TCP 的 HTTP/2，支持可选的 TLS 传输层加密。
- **协议包命名空间：** `synapse.hft`

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

### 1.1 gRPC RPC 方法详细解析

#### `Ping`
- **请求参数：** `Empty`
- **响应参数：** `SystemState`（返回服务器当前状态、激活布尔标志以及 UTC 毫秒时间戳 `server_time`）。
- **设计延迟目标：** $< 1\text{ ms}$

#### `LoadScenario`
- **请求参数：** `ScenarioDefinition`（传输压缩后的二进制路网几何数据 `.net.xml.gz`、拓扑图节点/边结构以及由 ADAGIO 分类器提取的高峰时段排期 JSON）。
- **响应参数：** `ScenarioStatus`（包含 `accepted` 准入布尔值与状态描述文本）。

#### `SystemControl`
- **请求参数：** `ControlCommand`（枚举控制动作：`START` 启动、`PAUSE` 暂停、`STOP` 停止、`RESET` 重置）。
- **响应参数：** `CommandResponse`（包含 `success` 成功标识与 `new_state` 目标状态字符串）。

#### `StreamTraffic`
- **请求参数：** `stream TrafficFrame`（高频客户端流式传输路段占有率、平均车速、排队长度与车辆密度）。
- **响应参数：** `SystemState`

---

## 2. 遥测与控制消息模式定义

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // 道路时间占有率比例 [0.0 - 1.0]
  float mean_speed = 2;     // 空间平均车速 (单位: m/s)
  int32 queue_length = 3;   // 排队驻停车辆数
  float density = 4;        // 道路密度 (单位: 辆/公里)
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

## 3. 进程间通信 (IPC) 队列技术规范

CARINA 统一协调由 [`ProcessManager`](../../src/launcher/process_manager.py) 管理的 11 个有界 IPC 队列与 1 个双工管道连接：

| 队列名称 | 最大容量 | 生产者进程 | 消费者进程 | 载荷模式 / 消息类型 |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Pipe | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Pipe | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | 全部 8 个微服务 | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | 用于写入 PostgreSQL 统计聚合的历史交通工程指标 |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | UI 指令、人工强制覆盖、手动配时与参数变更 |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | 内存中零端口实时遥测封包、拥堵评估与智能体成熟度 |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `InfrastructureClient` | 交通工程依据评估报告与信号配时优化建议 |
| **`mfd_trigger`** | 10 | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

关于通过 NTCIP 和 UTMC 对现场控制器进行物理控制的细节，请参阅 [硬件驱动程序](hardware_drivers.md)。

---

## 4. Prometheus 监控指标导出器规范

`MetricsManager` 在 **HTTP 8001 端口**（路径 `/metrics`）上暴露实时系统运行指标：

```text
# Prometheus 指标摘要说明:
carina_step_latency_seconds_bucket{le="0.005"}   # gRPC 遥测摄入至控制动作下发的端到端延迟直方图
carina_ppo_reward_total                          # PPO 战术智能体累计强化学习奖励总和
carina_guardian_veto_total{type="symbolic"}      # 符号安全防火墙强制否决累计计数器
carina_guardian_veto_total{type="neural"}        # PAE 神经网络溢流回堵否决累计计数器
carina_mfd_network_density_veh_km               # 全路网宏观车流密度
carina_mfd_network_flow_veh_hr                   # 全路网宏观车流通行能力
carina_active_processes_count                    # 当前存活的后台微服务子进程总数
```

---

## 5. 外部监控遥测与轮询传输协议 (`src/transports/`)

CARINA 通过 [`MonitorClient`](../../src/communication/monitor_client.py) 和 [`src/transports/`](../../src/transports) 向外部指挥调度大屏和云端遥测平台派发实时状态心跳及硬件警报。

### 5.1 遥测数据载荷结构

#### 异常事件告警载荷 (`noxfort/incidents/` 或 HTTP POST)
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

#### 保活心跳遥车载荷 (`noxfort/telemetry/` 或 HTTP POST)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

### 5.2 外部传输协议支持

| 传输协议 | 配置示例 (`CARINA_MQTT_HOST`) | 实现类 | 传输技术特性 |
| :--- | :--- | :--- | :--- |
| **MQTT Broker** | `127.0.0.1:1883` 或 `broker.emqx.io` | [`MonitorMqttTransport`](../../src/transports/mqtt_transport.py) | 基于 Paho MQTT v2，保活心跳 60s，发布主题 `noxfort/telemetry/` 与 `noxfort/incidents/`。 |
| **HTTP / HTTPS REST** | `https://monitor.noxfort.com/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | JSON `POST` 请求，复用持久化 `requests.Session`，支持指数退避重试，超时 3.0s。 |
| **云端穿透隧道 (Ngrok)** | `https://xxxx.ngrok-free.dev/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | 通过 `endpoint_resolver.py` 智能识别并通过安全的公网 HTTPS 隧道传输。 |

### 5.3 端点类型自动推断规则
工厂函数 [`create_monitor_transport()`](../../src/transports/factory.py) 能够自动解析配置的主机字符串并实例化对应的传输协议：
1. 若主机字符串以 `http://` 或 `https://` 开头 $\implies$ **HTTP 传输协议**。
2. 若主机字符串包含 `.ngrok`、`.run.app` 或 `/api/` 路径 $\implies$ **HTTP 传输协议**（若省略了协议头，自动补全 `https://` 前缀）。
3. 若主机字符串包含标准 IP 地址或域名及可选端口（如 `10.0.0.1:1883`） $\implies$ **MQTT 传输协议**。

---

## 6. 特种应急车辆遥测接入 HTTP API

Go 语言编译的 Web 网关对外提供高吞吐量、单向即发即弃的应急车辆高精 GPS 遥测接入端点：

- **API 路由：** `POST /api/v1/evp/telemetry`（别名：`POST /amb` 或 `POST /amb/`）
- **监听端口：** `2201`（Go Web 网关 / Tailscale Funnel）或 `8085`（独立 Go EVP 原生接收服务 [`src_go/evp_go/`](../../src_go/evp_go) / 独立接收器）
- **HTTP 响应：** `204 No Content`（亚毫秒级瞬时响应，无需等待底层处理）
- **载荷数据格式：**
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

## 7. Go 硬件与 Web 网关 NDJSON IPC 指令集

CARINA Python 核心层通过匿名标准管道（`stdin`/`stdout`）向 `bin/carina-go` 网关下发的控制指令集：

| 指令 (`cmd`) | 参数 / 载荷 | 返回数据 | 功能语义说明 |
| :--- | :--- | :--- | :--- |
| **`ping`** | 无 | `"pong"` | 探测网关进程连通活性（$< 1\text{ ms}$）。 |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `protocol`, `green_stages` | 连接元数据 | 与现场物理交通机建立 SNMP/UDP 通信会话。 |
| **`disconnect`** | `intersection_id` | `success: true` | 断开与指定交通机的网络连接并释放底层套接字。 |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | 将神经网络或安全防火墙决定的逻辑动作映射作用于物理信号灯组。 |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `vehicle_id` | 执行动作确认字符串 | 向现场控制器微秒级下发全绿波应急相位保持或释放指令。 |
| **`cco_broadcast`** | `data: dict` | `success: true` | 向已建立连接的 CCO SSE 大屏客户端广播实时路况遥测帧。 |
| **`tailscale_status`** | 无 | `TailscaleStatus` JSON | 查询当前 Tailscale Funnel 域名、节点互联状态以及 CCO 公网访问地址。 |
| **`emergency_release`** | 无 | `success: true` | 紧急无条件释放全城所有交叉口的所有相位保持锁定。 |

---

## 8. 中央控制调度中心 (CCO) REST 与 SSE 端点规范

在 Go Web 网关 `2201` 端口上提供服务（支持通过 Tailscale Funnel 进行加密穿透）：

- **`GET /health`**: 返回底层网关健康状态与服务可用性。
- **`GET /cco` 与 `GET /cco/`**: 提供编译完成的 React 18 CCO 网页客户端静态资源。
- **`GET /cco/stream`**: 基于服务器发送事件（SSE）的长连接，向大屏持续广播毫秒级信号灯相位、拥堵热力数据与应急特勤车辆轨迹。
- **`GET /cco/topology`**: 提供 GeoJSON/JSON 格式的道路拓扑几何坐标、车道连通关系以及交叉口绝对经纬度。

---

## 9. 训练步数节律、成熟度晋升与单周覆盖率工具模块

CARINA 核心 Python 接口，用于时序配时计算与生命周期进化控制：

### 9.1 `EpisodeStepCalculator` (`src.utils.episode_step_calculator`)
依据城市道路物理拓扑，动态计算每回合训练决策步数与安全底线：
- **`calculate(net_or_path: Union[str, Any], telemetry_delta_ms: float = 250.0) -> EpisodePacingResult`**
  解析 SUMO 路网，合并双向车道，剔除交叉口内部微连接（`:`），计算拓扑复杂度 $C_{\text{topo}}$、次线性物理松弛耗时 $T_{\text{physical}}$，并返回包含 `episode_steps`、`duration_seconds` 以及单周法定安全回合底线（`child_episodes_1_week`, `teen_episodes_1_week`）的 `EpisodePacingResult`。

### 9.2 `WeeklyCoverageTracker` (`src.core.weekly_coverage_tracker`)
以原子化磁盘持久化追踪覆盖真实日历全周 168 小时时空槽位（$7\text{ 天} \times 24\text{ 小时}$）：
- **`register_step(raw_timestamp: float) -> Tuple[int, int]`**：依据真实 UNIX 物理时间戳向 `(星期几, 小时)` 矩阵打卡登记。
- **`is_week_completed() -> bool`**：若整周 168 个小时槽位全部至少观测过一次，则返回 `True`。
- **`get_completion_ratio() -> float`**：返回当前单周覆盖完成度比例，范围 $[0.0, 1.0]$。
- **`save_state() / load_state()`**：将覆盖状态原子化读写至磁盘（`weekly_coverage_{phase}.json`），耐受进程暂停与节点重启。

### 9.3 `ActionAuthorizer` (`src.core.action_authorizer`)
依据智能体成熟度生命周期阶段与真实日历时间，严格鉴权物理硬件控制权：
- **`is_action_authorized(agent_id: str, maturity: Maturity, sim_time: float, raw_timestamp: float = 0.0) -> Tuple[bool, str]`**：判断智能体是否有权接管物理现场控制器。强制限制 `TEEN` 阶段智能体仅在非高峰时段控制硬件，而在经典早晚高峰（周一至周五 06:30-09:00 与 17:00-19:30）或 Synapse 动态高峰期间强制退回影子模式。
- **`load_peak_schedule_json(schedule_data: dict) -> None`**：载入由感知层 Synapse 推送的动态高峰排程字典。

### 9.4 `MaturityPacingCalculator` (`src.promotion.maturity_pacing_calculator`)
- **`calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]`**：返回受 1 周法定安全底线钳位的 `(child_episodes, teen_episodes, child_steps, teen_steps)`，满足 $E_{\text{week}} \times S \times \Delta t \ge 604\,800\text{ 秒}$。
- **`apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool`**：将计算求得的动态节律参数自动注入 `MaturityManager`。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
