---
tags: [architecture, core, system, gatv2, pae, pbt, amp, multiprocessing]
aliases: [系统架构, 多进程蓝图, 系统全景概览]
---

# 🏛️ CARINA：系统蓝图与多进程并发架构

本文档详尽规范了 CARINA 生态系统的内部工程架构。深入解析了 8 个操作系统并发微服务、规范深度神经网络拓扑结构（LocalAgent PPO-TCN、GuardianAgent D3QN 与 StrategistAgent ST-GATv2 Lite）、`TopologicalScaler` 拓扑缩放器、物理交通机驱动程序以及 PostgreSQL 异步增量差分存储引擎。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🚨 查阅 [EVP 优先通行](evp_and_preemption.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🧠 查阅 [神经理论推导](research_notes.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md)

---

## 1. 多进程微服务并发模型

Python 的全局解释器锁（GIL）阻碍了计算密集型的 CPU/GPU 人工智能推理与高吞吐量 I/O 操作实现真正的多线程并行。为了实现严格的亚毫秒级控制响应，CARINA 采用了由 [`carina.py`](../../carina.py) 和 [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py) 编排的**多进程微服务模型**，并与工业级 **Go 硬件与 Web 网关**（`bin/carina-go`）无缝集成：

```mermaid
graph TD
    Launcher[carina.py 编排器 / UI 托盘] -->|派生与监控| PM[ProcessManager 进程管理器]

    PM --> CC[1. CentralController 进程]
    PM --> AI[2. AI_Process 推理引擎]
    PM --> WD[3. Watchdog 看门狗进程]
    PM --> SDS[4. DashboardService SDS 仪表盘服务]
    PM --> SAS[5. AnalysisService SAS 分析服务]
    PM --> DB[6. StepDecisionWorker 与 DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM 分析进程]
    PM --> MFD[8. MFD_Worker 宏观动力学引擎]

    CC <-->|IPC 管道| AI
    CC -->|wd 队列 (心跳)| WD
    AI -->|db 队列| DB
    CC -->|sds 队列| SDS
    CC -->|sas 队列| SAS
    CC -->|mfd_trigger 队列| MFD
    MFD -->|mfd_results 队列| CC
    SAS -->|sas_results 队列| CC
    XAI -->|磁盘 HFT 日志| AI

    CC <-->|NDJSON 管道输入输出| GW[Go 网关 carina-go]
    GW --> NTCIP[NTCIP / UTMC 现场交通机 UDP 161]
    GW --> WebGW[Go Web 网关 端口 2201 / Tailscale]
    WebGW --> CCO[CCO Web 大屏地图 React/TSX src_tsx]
    WebGW <--|POST 204 遥测上报| EVP[EVP GPS 车载天线 端口 8085]
```

---

## 2. 深度学习神经网络前沿架构

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │   自动检测路网节点数 (N) -> 隐空间维度 (32/64/128/256), 注意力头数 (2/4/8/16) │
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │     LOCAL AGENT (PPO)       │           │   STRATEGIST AGENT (GRAPH)  │
     │  战术级 TCN 时序卷积主干    │           │   ST-GATv2 Lite 宏观协调器  │
     │  （毫秒级实时信号配时决策） │◄──────────┤   （干道绿波协调控制）      │
     └──────────────┬──────────────┘Context Vec└──────────────┬──────────────┘
                    │                                         │
                    │ 提议动作                                │ 全网路况拓扑上下文
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │   神经符号双重安全护盾、溢流回堵防御与交通安全否决机制                │
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 ST-GATv2 Lite 模块 (`src/models/st_gatv2_lite.py`)
- **设计目标：** 实现城市道路交通拓扑图上相邻路口之间干线“动态绿波带”的空间相位同步。
- **动态权重机制：** 尽管物理道路拓扑是静态固定的，但动态空间注意力系数 $\alpha_{ij}(t)$ 会根据实时汇入车辆密度与速度梯度进行毫秒级在线重计算。
- **去中心化协同：** 战略协调智能体（Strategist）周期性计算覆盖全路网的时空上下文张量，并注入给本地智能体（LocalAgent）与守卫智能体（GuardianAgent），从而在无需脆弱中心单点决策的前提下自发涌现干线绿波协同。

### 2.2 通用预测自编码器 Universal PAE (`src/models/pae.py`)
- **设计目标：** 共享的高容量物理动态特征提取引擎，将多步序贯交通物理动态压缩映射至结构不变的潜在低维空间 ($Z \in \mathbb{R}^{16\dots 128}$)。
- **精准赋能：** 为本地策略决策（LocalAgent）与溢流回堵审计（GuardianAgent）提供紧凑的时序物理预测表征。

### 2.3 $O(1)$ 拓扑自适应缩放器 (`src/utils/topo_scaler.py`)
- **算法级自适应：** 自动探测路网交叉口规模（$N$ 个节点），自主调整以 2 的幂次对齐 NVIDIA TensorCore 计算架构的最佳神经网络超参数：
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$（如巴西隆德里纳Londrina大都市路网）
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$（超大城市级路网拓扑）

### 2.4 通用 AMP 与 TensorCore 硬件加速
- 核心模型的前向推理计算全部被封装在 `torch.amp.autocast` 混合精度上下文中，原生启用 NVIDIA TensorCore 的 FP16/TF32 硬件算力加速，将核心模型全生命周期的显存（VRAM）占用严格限制在 **约 20 MB**。

---

## 3. 持久化数据层与增量压缩存储引擎

CARINA 实现了基于 PostgreSQL **游程增量差分压缩编码（Run-Length Delta Compression）** 的异步数据持久化引擎：
- **`step_decisions`**：通过非阻塞 RAM 环形队列将配时建议、Guardian 符号否决记录与步进计时器异步派发至 [`StepDecisionWorker`](../../src/database/step_decision_worker.py)，调度开销 $< 0.001\text{ ms}$。
- **`edge_dictionary`**：将长字符串路段名称哈希映射为 4 字节紧凑整数进行全局索引。
- **存储优化效果：** 实现了高达 **97.9% 的磁盘存储占用缩减**（对于拥有 200 个路口的都市级路网，全量时序记录仅占用约 380 MB/天）。

有关数据库模式与详细 SQL 查询定义，请参阅 [数据库架构与模式](database_and_schemas.md)。

---

## 4. 模块化配置架构 (`src/settings/`)

为了彻底贯彻**单一职责原则**（Single Responsibility）与**接口隔离原则**（Interface Segregation，SOLID），CARINA 的配置管理架构被解耦为独立的组件：

```text
       ┌────────────────────────────────────────────────────────┐
       │               SettingsService (Orchestrator)           │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(校验与段映射) │     │& Write 接口  │ │(settings.ini   │ │(.env 12-Factor 规范  │
│               │     │              │ │ 文件读写)      │ │ 环境变量机密)        │
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ 向后兼容适配门面
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`):** 权威注册表，定义配置键与配置段的映射关系、默认回退值以及强类型校验规则。
- **`IniFileStorage` (`src/settings/ini_storage.py`):** 处理对 `config/settings.ini` 文件的物理读取与持久化回写。
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** 基于 12-Factor 原则，通过 `python-dotenv` 解析 `.env` 中的敏感基础设施凭据，支持自动文件解析回退。
- **`SettingsService` (`src/settings/service.py`):** 核心配置服务，统筹配置检索、验证与序列化全流程。
- **`SettingsManager` (`src/utils/settings_manager.py`):** 即插即用的向后兼容适配门面，确保遗留调用代码零改动、零回归。

---

## 5. 多态监控与传输架构 (`src/transports/`)

CARINA 具备**多态遥测与异常事件传输层**，支持通过本地 MQTT Broker、远程 Webhook、云端 REST API 或安全穿透隧道（如 Ngrok）进行实时远程监控：

```text
IncidentReporter 异常上报 / TelemetryLoop 遥测循环
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (单例门面)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (具备自动端点解析的工厂)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│ (本地 / 局域网 MQTT Broker)│             │ (REST API / 云平台 / Ngrok)│
│ - 主机:端口 (如 :1883)    │             │ - http:// 或 https://     │
│ - QoS 0/1 遥测数据流      │             │ - 长连接 HTTP Session     │
│ - 主题: noxfort/telem/    │             │ - 指数退避重试机制        │
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 传输抽象规范 (`BaseMonitorTransport`)
为所有外部遥测导出器定义了严格契约：
- `setup()`: 配置目标端点、超时阈值与安全凭证。
- `ensure_connected()`: 建立或校验物理网络连通性。
- `publish(topic, payload)`: 在独立工作线程中异步发布 JSON 载荷。
- `disconnect()`: 刷写待发缓存并优雅切断通信会话。

### 5.2 自动端点智能解析 (`endpoint_resolver.py`)
无需显式声明协议即可智能研判目标端点类型：
- 以 `http://` 或 `https://` 开头（或域名包含 `ngrok`、`run.app`、`/api/`）自动实例化 `MonitorHttpTransport`。
- 标准主机名/IP 字符串（如 `localhost`、`10.0.0.1`、`broker:1883`）自动实例化 `MonitorMqttTransport`。

### 5.3 异常事件去重与告警过滤 (`src/drivers/`)
- [`IncidentReporter`](../../src/drivers/incident_reporter.py) 负责向外部监视中心广播硬件连通性状态切换与交通机故障。
- [`IncidentFilter`](../../src/drivers/incident_filter.py) 通过基于时间戳防抖的有状态哈希缓存消除告警风暴，在系统重启周期中通过 `.carina_incident_filter_cache.json` 保持缓存状态连续性。

---

## 6. 高性能现场硬件通信网关 (`src_go/`)

为了在实际部署环境中达到工业级可靠性、亚毫秒级网络确定性并彻底免除 Python GIL 锁争用，CARINA 将所有底层物理信号机通信（UDP 端口 161 与 162）卸载至专用的独立编译型 **Go 语言硬件网关**（由 `src_go/` 编译生成的 `bin/carina-go`）：

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │   [Synapse Perception]  <-- gRPC (50051) -->  [Camera] │
       │            │                                           │
       │      [AI Engine / NN]                                  │
       │            │                                           │
       │     [ActionSupervisor]                                 │
       │            │                                           │
       │ [HardwareConnectionManager] (Python 编排器)            │
       │            │                                           │
       │    [GoGatewayClient] (管道子进程管理器)                 │
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout（换行符分隔的 JSON / NDJSON）
                    │ 主机零开放网络端口 (ZERO OPEN NETWORK PORTS)
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │          CARINA HARDWARE GATEWAY (Go 守护进程)         │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [NDJSON IPC 扫描器与并发写入器]                   │
       │  +-- [HardwareManager 连接注册表]                      │
       │  +-- [遭遇 EOF / SIGPIPE 触发原子级故障安全回退]       │
       │  +-- [心跳引擎: time.Ticker 单路口独立心跳]            │
       │  +-- [NTCIP 1202 与 UTMC2 协议调度器]                  │
       │  +-- [GoSNMP 客户端连接池 (UDP 161)]                   │
       │  +-- [TrapListener 告警监听服务器 (UDP 162)]           │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Traps)
                            ▼                  ▼
                    [现场交通机]        [现场交通机] ...
```

### 6.1 核心架构特性
- **主机零网络端口开放：** Python 与 Go 之间的控制链路完全通过标准匿名管道（基于 Linux 内核环形缓冲区 `pipe(2)`）运行，杜绝在本地主机暴露任何 TCP/HTTP 监听端口。
- **原子级安全故障回退：** 一旦 Python 人工智能主进程发生崩溃或异常关闭，内核会即刻关闭管道。Go 二进制文件在微秒级内捕捉到 `os.Stdin` 的 `EOF` 信号，立即向所有受控路口广播 `EmergencyReleaseControlAll()` SNMP 指令，安全释放远程锁定，促使信号机瞬间回退至本地固化自主配时方案。
- **彻底消除 GIL 争用：** 由 Goroutine 完全独立于 Python PyTorch 张量运算，高并发执行周期轮询、2.0秒保活心跳与 UDP 162 Trap 陷阱监听。
- **无缝透明适配器 (`GoTrafficDriverProxy`)：** 严格遵循里氏替换原则（LSP）实现 `BaseTrafficDriver` 抽象接口，对 CARINA 现有业务逻辑层 100% 透明无感。

---

## 7. F.E.N.I.X. 进程监管与崩溃自愈子系统 (`src/fenix/`)

CARINA 深度集成了 **F.E.N.I.X.**（Fault-tolerant Engine for Networked Intelligent eXecution，网络化智能执行容错引擎），以确保 AI 推理引擎在 7×24 小时无人值守环境下的自主恢复能力：

```text
       ┌────────────────────────────────────────────────────────┐
       │                 Watchdog 健康监视器                    │
       └───────────────────────────┬────────────────────────────┘
                                   │ 超时 / 心跳丢失
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            FenixSupervisor (自愈编排器)                │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- 滑动时间窗口指数退避      │ │- 子进程全生命周期管理   │
       │- 最大重启配额限制器        │ │- SIGTERM / SIGKILL 信号 │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ 重新生成
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- FROZEN_SYNC 冻结遥测   │
                                      │- 周期边界安全握手       │
                                      │- 零冲突控制权交接       │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`):** 统一调度子进程终止、恢复退避、子进程拉起与系统状态对齐。
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** 计算指数退避惩罚并强制执行重启配额，坚决防范级联崩溃雪崩风暴。
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** 底层子进程管理模块，确保严格的进程隔离与确定性的 SIGTERM/SIGKILL 优雅终止。
- **`StateReconciler` (`src/fenix/state_reconciler.py`):** 确保重生后的 AI 引擎首先以 `FROZEN_SYNC`（冻结同步）模式平稳运行，仅当现场物理控制器自然过渡至绿灯周期边界时，才接管实际控制权。

---

## 8. 智能体生命周期、相位内 PBT 与晋升引擎 (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA 将强化学习策略设计为历经 3 个成长阶段的进化有机体：

```text
  ┌──────────────────┐        熵衰减与步频对齐            ┌──────────────────┐       熵与流体裕度 (delta*)               ┌──────────────────┐
  │   幼年期 CHILD   │ ─────────────────────────────────> │   青年期 TEEN    │ ───────────────────────────────────────>  │   成年期 ADULT   │
  │  (影子观察模式)  │                                    │ (平峰自主试运行) │                                           │ (全自主控制权限) │
  └────────┬─────────┘                                    └────────┬─────────┘                                           └────────┬─────────┘
           │                                                       │                                                              │
           ▼                                                       ▼                                                              ▼
  [受免疫保护隔绝 PBT]                                    [相位内 PBT 进化]                                             [相位内 PBT 进化]
  [被动观测流体动力学]                                    (仅限 TEEN <-> TEEN)                                          (仅限 ADULT <-> ADULT)
  [法定单周安全底线]                                      [早晚高峰强制影子]                                            [7x24小时全权控制]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`):** 核心应用服务与统一门面，统筹评估智能体成熟度，辅以充血实体 `AgentMaturity`、`MaturityConfig` 与 `MaturityPromotionService`。
- **`PopulationManager` (`src/core/population_manager.py`):** 负责执行**相位内群体进化算法（Intra-Phase Population-Based Training）**。智能体仅在同层级伙伴之间克隆与变异（`TEEN` 对 `TEEN`，`ADULT` 对 `ADULT`），而 `CHILD` 智能体受到保护隔绝。内嵌张量形状严格验证，避免因异构路口输入维度不一致引发崩溃。
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`):** 严密校验香农策略熵（Shannon Policy Entropy）、最小回合时长与目标性能指标。
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`):** 依据路网物理拓扑（合并往返双向车道、剔除交叉口内部微连接 `:`、结合 $\sqrt{N}$ 与 $D_{\text{km}}$ 次线性松弛）动态量化单回合步数，精确计算满足连续 7 天观测的最少回合底线（$E_{\text{week}}$ 回合，在 $\Delta t = 250\text{ ms}$ 条件下）。
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`):** 原子化持久化追踪 168 小时全周时空日历矩阵（$7\text{ 天} \times 24\text{ 小时}$），保证系统进程随时停机重启或异常崩溃后考察历史无损续接。
- **`ActionAuthorizer` (`src/core/action_authorizer.py`):** 严格约束 `TEEN` 阶段智能体的现场控制权，在经典城市高峰（周一至周五 06:30-09:00 与 17:00-19:30）或 Synapse 动态高峰时段强制退回影子模式。
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`):** 统筹时序节律引擎，融合 `EpisodeStepCalculator` 并严格执行法定单周安全底线不变量（$t_{\min} = \max(E_{\text{week}}, \text{配置值})$）。
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`):** 基于来自 `synapse_fluid_dynamics` 的实测通行速度与道路占有率，动态计算毕业晋升所需的超额性能增益阈值 $\delta^* \in [3.0\%, 25.0\%]$。

---

## 9. 物理奖励平衡子系统 (`src/engine/reward_weights_calculator.py`)

为了消除因累计排队等待时间远超车辆通行吞吐量数量级而导致的梯度失真，CARINA 根据美国道路通行能力手册（HCM）的物理路段行程时间动态平衡奖励函数：

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`):** 在路网拓扑加载完成时（`TopologyManager.load_topology`）自动计算归一化的奖励权重系数。
- **`RewardCalculator` (`src/engine/reward_calculator.py`):** 通过 `set_reward_weights` 动态摄入平衡权重，在车流放行奖励与排队延误惩罚之间建立动态物理均衡。

---

## 10. 夜间黄闪定时调度子系统 (`src/controller/yellow_schedule_manager.py`)

为满足低流量夜间时段的道路交通安全与法规合规要求，CARINA 内置了自主黄闪定时调度子系统：
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`):** 实时比对配置的时间窗口（如 23:00 至次日 05:00）与系统时钟，自主向底层硬件发送黄闪指令，并在时间窗口结束边界平滑切回 AI 自适应控制。
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`):** 前端交互卡片，支持运维工程师按需启用/禁用黄闪计划、自定义起止时段，并可灵活绑定单个路口或全网应用。

---

## 11. 应急车辆优先通行 (EVP) 子系统 (`src/evp/`, `src_go/evp_go/`)

为赋予急救车（SAMU）、消防车与警车等应急特种车辆毫秒级通行的自主“全绿波生命通道”，且完全符合巴西 CONTRAN 第 960 号决议与 CTB 第 29 条法规要求，CARINA 构建了专用 EVP 子系统：

```text
 GPS 车载定位 / 信号信标     Go Web 网关 (:2201 / :8085)          EVPService (src/evp/)
           │                             │                                   │
           │── POST /api/v1/evp/telemetry ─>│                                   │
           │   (HTTP 204 No Content)     │── NDJSON / 进程内数据流 ─────────>│
           │                             │                                   ├── 运动学判定 (Haversine WGS84)
           │                             │                                   ├── 进入门限判定 (60m <= d <= 160m)
           │                             │                                   └── 警报警灯状态校验
           │                             │                                           │
           │                             │                                           ▼
           │                             │                                 SafetyAuditor 安全审计 (规则 #0)
           │                             │                                 (黄灯/全红清空 -> ACTION_HOLD 保持)
           │                             │                                           │
           │<───── 全绿波应急走廊 ───────┼── SNMP ascPhaseHold (Go 优先调度器) <─────┘
```

- **双因子触发机制：** 优先通行权限的授予必须同时满足物理接近进入门限（$60\text{ m} \le d \le 160\text{ m}$）以及紧急警报开启状态（`siren_active = True`）。
- **SafetyAuditor 优先级拦截：** 规则 #0 优先拦截一切 AI 配时决策，在严格遵守法定黄灯及全红清空安全间隔的前提下，强制锁定通行相位（`ACTION_HOLD = 1`）。
- **CONTRAN 45 秒看门狗硬限制：** 连续绿灯保持时间严禁超出 45 秒，超限强制释放以防交叉方向发生锁死。
- **即时撤销机制：** 车辆一旦驶越路口停止线（$d \le 15\text{ m}$），优先特权立即解除。

完整工程规范详见 [应急车辆优先通行 (EVP)](evp_and_preemption.md)。

---

## 12. 中央控制调度中心 (CCO) Web 架构 (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA 为市政交通指挥大屏与远程调度提供现代化 Web 运维中心：
- **`WebGatewayServer` (`src_go/web_gateway/server.go`):** 运行于 2201 端口的内嵌高性能 Go HTTP 服务器，提供 SSE 实时事件流（`/cco/stream`）、路网拓扑端点（`/cco/topology`）以及 Tailscale Funnel 安全远程穿透支持。
- **`CCO Web Application` (`src_tsx/src_cco/`):** 基于 React 18、TypeScript、Tailwind CSS、SVG 矢量地图渲染器与 Apache ECharts 的现代仪表盘，实时呈现车辆微观位置轨迹、信号灯相位倒计时以及 EVP 优先警报浮窗。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
