---
tags: [moc, hub, docs, obsidian, carina, index]
aliases: [CARINA MOC, 核心文档中心, 文档索引, 知识库]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA 官方技术主文档中心 (MOC)
### 核心索引与多智能体架构知识库
*Noxfort Systems — A State Of Art Company*

</div>

欢迎查阅 **CARINA**（Controlled Artificial Road-traffic Intelligence Network Architecture，受控人工道路交通智能网络架构）技术文档库。CARINA 作为面向实时交通信号灯控制的大规模并发、高频深度强化学习生态系统，在高级神经符号人工智能、实时 gRPC 硬件控制以及多进程操作系统隔离之间建立了工业级桥梁。

本主文档索引为核心开发者、学术研究人员、市政交通工程师以及系统集成商提供了系统深度的技术覆盖。该索引完全兼容 **GitHub** 与 **[Obsidian](https://obsidian.md/)** 双向链接。

---

## 🗺️ 代码库全景图与目录层级

```text
CARINA_CORE/
├── carina.py                   # 主编排器（SingleInstanceLock, ProcessManager, UI/托盘管理）
├── ARCHITECTURE.md             # 8进程多进程蓝图与 IPC 拓扑结构
├── pyproject.toml              # 构建工具链与项目元数据
├── requirements.txt            # Python 运行时依赖库
├── .env.example                # 12-Factor 应用环境变量与安全凭据模板
│
├── config/                     # 配置系统
│   ├── settings.ini            # 全局参数（AI、PBT、看门狗、MFD、日志）
│   ├── database/               # 动态 SQL 查询与模式（schema_queries.json, fluid_dynamics_queries.json）
│   ├── rules/                  # 安全与语义一致性规则（safety_rules.json, semantic_rules.json）
│   └── templates/              # 多语言报表、MFD、SAS 与 XAI 模板
│
├── packaging/                  # 密封式 Debian 打包规范与配置
│   ├── Dockerfile.build        # 多阶段密封式构建器（Node、Go、Python、dpkg-deb）
│   └── deb/                    # Debian 控制文件、systemd 服务单元与安装后脚本
│
├── scripts/                    # 编译、自动化与内存受限测试脚本
│   ├── build_deb.sh            # 容器化 Debian 安装包构建脚本
│   └── pytest_limited.sh       # cgroup v2 / ulimit 限制内存的 Pytest 运行器（上限 2 GB）
│
├── proto/                      # gRPC 协议规范
│   └── synapse_hft.proto       # 高频遥测与执行控制 Protobuf 定义
│
├── docs/                       # 综合知识库
│   ├── CARINA_MOC.md           # 核心主文档中心（本文件）
│   ├── index.md                # MkDocs 入口与门户
│   ├── ARCHITECTURE.md         # 8进程多进程蓝图与 IPC 拓扑结构
│   ├── EVP_AND_PREEMPTION.md   # 应急车辆优先通行 (EVP)、Go Web 网关与 CCO 大屏
│   ├── API_REFERENCE.md        # Synapse HFT gRPC 协议与 IPC 队列模式
│   ├── RESEARCH_NOTES.md       # PPO-TCN、PAE、GATv2 与 DA SILVA 数学理论公式
│   ├── HARDWARE_DRIVERS.md     # 物理交通机：NTCIP 1202、UTMC2 与 SNMP 集成
│   ├── SAFETY_AND_WATCHDOG.md  # Guardian 安全防火墙、否决规则与看门狗
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # MUTCD / FHWA 交通信号设置依据 1, 2, 3, 4
│   ├── MFD_AND_ANALYTICS.md    # 宏观基础图 (MFD) 与路网密度动态分析
│   ├── DATABASE_AND_SCHEMAS.md # 持久化层、异步增量存储与 SQL 数据库模式
│   ├── XAI_AND_SAS.md          # 可解释人工智能、Captum 积分梯度与 SAS 深度分析
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # 模块化 ABNT Word (.docx) 与 OMML 数学公式
│   ├── SLM_AND_LOCAL_LLM.md    # 端侧离线大模型集成（Qwen3.5 2B / llama.cpp）
│   ├── UI_AND_DASHBOARD.md     # Flet 桌面端应用程序、规划视图与 SDS 架构
│   ├── RENDERING_AND_HEATMAPS.md # 矢量地图渲染与异步热力图空间插值
│   ├── SECURITY_AND_AUTH.md    # 用户账户、加盐 PBKDF2 HMAC SHA-256 哈希与防暴力破解锁定
│   ├── DEVELOPER_GUIDES.md     # 开发环境配置、智能体层级、配置管理与打包
│   ├── TESTING.md              # Pytest 测试套件、硬件模拟桩与覆盖率验证
│   └── DEPLOYMENT_AND_PACKAGING.md # Docker 镜像构建、Systemd 守护进程与 Debian 软件包
│
├── bin/                        # 编译后的原生二进制文件（carina-go）
├── src_go/                     # Go 语言硬件与 Web 网关（NTCIP、UTMC、EVP、Web Gateway）
│   ├── cmd/gateway/            # 网关入口与 NDJSON 管道 IPC 循环
│   ├── configs/                # 内嵌 NTCIP 与 UTMC OID JSON 配置文件
│   ├── evp_go/                 # 微秒级 EVP 优先通行调度器
│   ├── pkg/                    # snmp、ntcip、utmc、discovery、heartbeat、traplistener、manager
│   └── web_gateway/            # HTTP/SSE 网关（端口 2201）、Tailscale 网格网络与 CCO 处理器
├── src_tsx/                    # 中央控制调度中心 (CCO) Web 应用
│   └── src_cco/                # React 18、TypeScript、Tailwind CSS、SVG 地图层、ECharts
├── src/                        # 核心源代码
│   ├── agents/                 # PPO LocalAgent、GuardianAgent、PAEStateAugmentor 与 Checkpoints
│   ├── analysis/               # MUTCD WarrantEvaluator、WarrantMath 与交通工程分析
│   ├── blocks/                 # 模块化 .docx 构建器、OMML 数学转换器与缓存格式化器
│   ├── central_controller.py   # 高频 gRPC 遥测服务器与网关所有者 (Gateway Owner)
│   ├── communication/          # MonitorClient、HFT gRPC 安全 (TLS/mTLS/Bearer) 与 ThreadSafePipe
│   ├── controller/             # HardwareGatewayCoordinator、ConnectionManager、FenixStageDispatcher 与覆盖控制
│   ├── core/                   # DecisionCoordinator、SafetyAuditor、ActionAuthorizer 与 PopulationManager
│   ├── database/               # DatabaseEngine、PostgresConnectionPool、SQLite WAL 与 StepDecisionWorker
│   ├── drivers/                # Go 网关代理、RemoteHardwareDriverProxy、HardwareTelemetryDecoder 与 Trap 桥接
│   ├── engine/                 # StepProcessor、BatchedPAEEncoder、FleetBatchInferencer (vmap) 与 PhysicalActionMasker
│   ├── evp/                    # 应急车辆优先通行 (EVPService、EVPSnapshotSynchronizer、Kinematics)
│   ├── fenix/                  # F.E.N.I.X. 自愈与进程监管（Supervisor、Runner、Reconciler）
│   ├── handlers/               # AI 请求、UI 命令与看门狗指令处理器
│   ├── interfaces/             # 隔离的 SOLID 协议契约 (Controller, Drivers, Engine, Repositories)
│   ├── launcher/               # ProcessManager、BackendServiceRegistry、FenixSupervisionLoop 与 WorkerEntrypoints
│   ├── manager/                # CycleManager、StageTransitionManager、AgentPopulationLoader 与 ServiceManager
│   ├── maturity/               # MaturityManager、AgentMaturity、PromotionService、Config 与 Port
│   ├── mfd/                    # 宏观基础图 (MFD) 分析器与工作进程
│   ├── models/                 # 统一 TCN 主干、ActorCriticNet、iTransformer PAE、QR-D3QN 与 ST-GATv2 Lite
│   ├── optimizer/              # 基于种群的训练 (PBT)、主机 NumPy PPO 与 DQN 优化器
│   ├── promotion/              # MaturityPacingCalculator、PerformanceMarginCalculator 与 PromotionEvaluator
│   ├── rendering/              # StaticMapRenderer、AsyncHeatmapRenderer 与离屏 mpl_utils
│   ├── repositories/           # StepDecisionRepo、FluidDynamicsRepo、HardwareConnectionRepo 与 ConnectionCSVStore
│   ├── safety/                 # GuardianPhysicsEstimator、GuardianRiskCalibrator (Noisy-OR)、GuardianShadowTrainer 与 Checkpoints
│   ├── sas/                    # 智能分析系统（Smart Analysis System，离线基础设施依据）
│   ├── sds/                    # 智能仪表盘服务（Flet UI 桥接、WebSockets 与证书固定 CCOBroadcastClient）
│   ├── security/               # 独立解耦安全子系统（Auth、PBKDF2、Lockdown、Repositories）
│   ├── settings/               # 模块化配置（SOLID 接口、模式、INI 与 .env）
│   ├── slm/                    # 端侧轻量大语言模型（Qwen3.5 2B、pynvml 显存探测与 slm_process_lock）
│   ├── transports/             # 多态外部传输（Base、HTTP、MQTT、EndpointResolver）
│   ├── utils/                  # SettingsManager、MetricsManager、路径、SumoNetCache 与周期步数计算
│   ├── watchdog/               # 实时进程心跳监视器与故障安全回退
│   └── xai/                    # 积分梯度归因分析、带缓存的多智能体报告构建器与工作进程
│
├── ui/                         # 原生 Flet 桌面端应用程序
│   ├── cards/                  # 模块化设置与遥测卡片（RemoteGateway、Hardware、EVP）
│   ├── controllers/            # DashboardDataCoordinator 与 RemoteGatewaySettingsPersister
│   ├── handlers/               # 事件处理器、SettingsHandler 与原生系统托盘 SystemTrayHandler
│   ├── views/                  # DashboardView、PlanningView、DiagnosticsView、SettingsView
│   ├── widgets/                # LiveCanvasMapWidget、PlanningControlPanel、MFDViewer、分页 AuditLogWidget
│   ├── renderers/              # PlanningMapRenderer、MapVisualSyncer、MapDrawer
│   ├── animators/              # MapAnimator（隐藏窗口暂停与脏标记门控）
│   └── locales/                # 多语言 JSON 字典（pt_br、en_us、es_es、zh_cn 等）
│
└── tests/                      # Pytest 测试套件（967 个已收集测试，memory_guard.py）+ src_go/ 中的 46 个 Go 测试
```

---

## 📖 系统维度与知识库导航指南

### 1. 核心基础设施与硬件驱动
- **[系统架构深入解析](architecture.md)**：详尽的技术蓝图，剖析 8 个操作系统并发微服务、基于 `multiprocessing` 的进程隔离、IPC 管道/队列通道以及执行主循环。
- **[硬件驱动与物理控制器](hardware_drivers.md)**：编译型 Go 硬件网关 (`carina-go`)、标准管道 NDJSON IPC、NTCIP 1202 (ASC)、英国标准 UTMC / UTMC2、SNMP v2c/v3 客户端、连接池管理以及确定性硬件故障安全回退规范。
- **[API 接口参考与 HFT 协议](api_reference.md)**：`Synapse HFT` gRPC 接口、外部监控遥测传输（MQTT/HTTP）、Prometheus 指标端点（端口 8001）以及进程间 IPC 队列模式的完整技术规范。
- **[数据库架构与关系模式](database_and_schemas.md)**：`DatabaseWorker`、`StepDecisionWorker`、连接池技术、12-Factor `.env` 配置规范以及 PostgreSQL 增量差分压缩存储（空间减少 97.9%）。
- **[安全机制与身份认证](security_and_auth.md)**：用户账户管理、加盐 `PBKDF2 HMAC SHA-256` 散列存储、防暴力破解锁定防护机制与基于角色的权限控制 (RBAC)。
- **[模块化配置架构](architecture.md#4-模块化配置架构-srcsettings)**：遵循 SOLID 原则的配置子系统，实现数据模式、INI 持久化存储与 12-Factor `.env` 机密的彻底解耦。
- **[多态监控与传输架构](architecture.md#5-多态监控与传输架构-srctransports)**：基于 MQTT Broker 与 HTTP/HTTPS REST/Ngrok 云端网关的遥测及异常事件流式传输。

### 2. 人工智能与神经符号安全机制
- **[神经理论研究与数学推导](research_notes.md)**：PPO-TCN、预测自编码器 (PAE) 潜在表征投影 $Z$、Dueling DQN-TCN 状态价值/优势流分离、ST-GATv2 Lite 时空图注意力以及 DA SILVA 课程学习机制的深度数学推导。
- **[安全架构、看门狗与 F.E.N.I.X.](safety_and_watchdog.md)**：物理符号否决规则 (SR-00 至 SR-06)、PAE 神经否决阈值、实时看门狗心跳监视 (< 500 ms) 以及具备清晰状态对齐机制的 F.E.N.I.X. 自主进程复活架构。
- **[可解释人工智能 (XAI)、SAS 与 MFD 分析](xai_and_sas.md)**：模块化 XAI 生产管线、Captum 积分梯度归因分析以及市政法医级司法审计体系的操作实现。
- **[报告模块引擎与 Word 自动生成](report_blocks_and_templates.md)**：符合 ABNT NBR 14724 规范的 Word (`.docx`) 报告自动化排版生成，原生内嵌 Office 数学标记语言 (OMML) LaTeX 公式。
- **[端侧轻量大语言模型 (SLM)](slm_and_local_llm.md)**：基于 Qwen3.5 2B / llama.cpp 的 100% 离线端侧 LLM 本地推理，生成司法取证级别的文字分析，杜绝云端数据泄露风险。

### 3. 交通工程流体力学、法定依据与图形学
- **[交通工程信号设置法定依据](traffic_engineering_warrants.md)**：MUTCD / FHWA 法定信号控制设置依据（依据 1 至 4）及基础设施改建依据的自动化算法评估。
- **[宏观基础图 (MFD) 与宏观动力学](mfd_and_analytics.md)**：全路网流量-密度宏观物理学、临界密度 ($K_{crit}$)、边界周界门控控制、通行能力骤降抑制以及突发事件滤波缓存机制。
- **[矢量地图渲染与空间热力图](rendering_and_heatmaps.md)**：SUMO `.net.xml` 路网文件的离线矢量解析与基于实时交通流的异步核密度估计 (KDE) 空间插值渲染。

### 4. 桌面交互前端与工程运维
- **[桌面 UI 与智能仪表盘服务](ui_and_dashboard.md)**：原生 Flet 桌面客户端架构、路网规划交互视图、单实例 Socket 互斥锁（端口 42123）以及基于 WebSocket 的实时数据流。
- **[开发者指南与系统扩展](developer_guides.md)**：开发环境搭建、配置文件修改、神经网络智能体定制与发布打包全流程指南。
- **[自动化测试与质量保证](testing.md)**：`pytest` 执行指南（共 967 个自动化测试，分布在 192 个单元测试、8 个集成测试与 4 个根目录测试模块中，外加 46 个 Go 测试）、`scripts/pytest_limited.sh` 内存上限控制、交通机驱动模拟桩以及 Guardian 安全否决验证。
- **[系统部署、打包与容器化](deployment_and_packaging.md)**：Docker 多阶段镜像构建 (`Dockerfile`)、Linux Systemd 守护进程单元以及 Debian `.deb` 安装包制作。

### 5. 应急优先通行与远程调度指挥 (EVP / CCO)
- **[应急车辆优先通行与远程控制](evp_and_preemption.md)**：应急车辆优先通行 (EVP) 核心引擎规范、CONTRAN/MUTCD 法规合规性、Haversine 运动学进出判定、双因子安全触发机制、45秒看门狗超时故障安全保护、Go 微秒级优先调度器、Tailscale Funnel 安全网格穿透以及中央控制调度中心 (CCO) 现代化大屏 Web 界面 (`src_tsx/src_cco`)。

---

> 💡 **Obsidian 知识图谱支持：** 本文档套件提供对 [Obsidian](https://obsidian.md/) 的原生完美支持。直接在 Obsidian 中将 `CARINA_CORE` 仓库根目录作为知识库（Vault）打开，即可交互式探索网状技术图谱和双向反向链接。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
