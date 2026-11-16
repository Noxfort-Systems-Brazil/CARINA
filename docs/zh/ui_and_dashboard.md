---
tags: [ui, flet, dashboard, frontend, sds, planning, widgets]
aliases: [UI交互架构, 仪表盘服务, Flet前端, 路网规划视图]
---

# 🖥️ 桌面 UI 架构、路网规划视图与智能仪表盘服务 (SDS)

本文档详尽规范了 CARINA 位于 [`ui/`](../../ui) 的原生桌面端用户图形界面、位于 [`src/sds/`](../../src/sds) 的**智能仪表盘服务 (Smart Dashboard Service, SDS)**、**系统托盘管理器 (System Tray Manager)** 以及单实例网络互斥运行锁机制。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🗺️ 查阅 [矢量地图渲染与热力图](rendering_and_heatmaps.md) | 🔍 查阅 [可解释人工智能与SAS](xai_and_sas.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 彻底解耦的桌面端微服务架构 (`ui/` 与 `src/sds/`)

为了彻底杜绝前端 GUI 渲染、窗口重绘或客户端浏览器网络卡顿对底层毫秒级实时信号控制决策产生反压，CARINA 将前端数据通信完全解耦至独立的 **`DashboardService` (SDS)** 操作系统进程（[`run_sds_worker`](../../src/sds/dashboard_worker.py)，以 `CARINA_GATEWAY_ROLE=remote` 模式运行）：

```text
CentralController (owner) ──> [sds 队列] ──> DashboardService (SDS) ──> [ui_telemetry 队列] ──> Flet UI (主线程)
                                                    ├──> WebSocket 遥测服务 (端口 8080, 2.0s 客户端超时与背压)
                                                    └──> CCOBroadcastClient (Pinned HTTPS -> Go Web 网关 :2201)
```

- **性能与内存保护机制 (`ui/` & `src/sds/`)：**
  - [`MapAnimator`](../../ui/animators/map_animator.py) 与 [`WindowManager`](../../ui/managers/window_manager.py)：当桌面窗口最小化或隐藏时（`_carina_window_hidden`）暂停地图重绘循环，并通过 `_data_dirty` 标志门控按需渲染。
  - [`AuditLogWidget`](../../ui/widgets/audit_log_widget.py)：对 Guardian 审计记录进行分页显示（每页 $\le 100$ 行），确保 Flet 表格始终保持瞬时刷新响应。
  - [`RemoteGatewaySettingsPersister`](../../ui/controllers/remote_gateway_settings_persister.py)：在 `settings.ini`、`SettingsManager`、`.env` 与运行时后端之间双向同步 `gateway_enabled` 配置。
  - [`EVPFleetConnectionCard`](../../ui/cards/evp_fleet_connection_card.py)：在 `will_unmount()` 生命周期钩子中确定性注销 `EVPNotifier` 监听器，防止内存泄漏。
  - [`DashboardDataCoordinator`](../../ui/controllers/dashboard_data_coordinator.py)：根据 IPC 遥测帧更新本地 `HardwareConnectionManager` 的被动镜像状态（`remote_hardware_status`）。

---

## 2. 真实 Flet UI 架构与视图层级体系

前端基于现代化跨平台框架 **[Flet](https://flet.dev/)**（Python 绑定与 Flutter 渲染引擎）开发，整体源码结构位于 [`ui/`](../../ui)：

```text
ui/
├── main_ui.py                      # Flet 应用程序启动入口与主窗口初始化
│
├── views/                          # 核心业务大屏视图
│   ├── dashboard_view.py           # 实时交通流监控与高帧率交互式电子地图画布
│   ├── planning_view.py            # 路网拓扑规划、相位方案配时与路段干道编组
│   ├── diagnostics_view.py         # 进程间 IPC 延迟、内存消耗与进程探针监视
│   ├── system_status_view.py       # 后台微服务存活性与物理交通机在线状态
│   ├── settings_view.py            # 系统配置总览与物理控制器 IP 端点管理
│   └── error_view.py               # 全局异常捕获与诊断分析视图
│
├── cards/                          # 模块化配置与监控卡片 (遵循开闭原则 OCP)
│   ├── evp_fleet_connection_card.py    # 特勤应急车队准入登记与 RFID/车载信标配置
│   ├── evp_safety_parameters_card.py  # 优先通行准入门限、最大驻留看门狗与清空间隔
│   ├── remote_gateway_card.py          # Go Web 网关启闭、2201 端口与 Tailscale 状态
│   ├── account_settings_card.py        # 调度人员档案、RBAC 角色权限与身份凭据
│   ├── database_settings_card.py       # 数据库引擎选型 (SQLite/PostgreSQL) 与自动迁移
│   ├── hardware_connection_card.py     # NTCIP 1202 与 UTMC 物理交通机连接池管理
│   ├── piloting_school_card.py         # 自主 PBT 进化调优节奏与强化学习晋升准则
│   ├── reward_weights_card.py          # 延误、车流压力、排队与车速物理奖励平衡权重
│   ├── traffic_rules_card.py           # 最短绿灯、黄灯过渡与全红安全清空间隔约束
│   ├── yellow_schedule_card.py         # 低谷夜间黄闪自主定时排期调度计划
│   ├── monitor_settings_card.py        # 外部 MQTT Broker / HTTP Webhook 遥测流配置
│   ├── advanced_system_card.py         # 看门狗超时熔断阈值、IPC 缓冲区深度与心跳频率
│   ├── advanced_dqn_card.py            # DQN 经验回放池容量、目标网络同步周期与探索率
│   └── advanced_ppo_card.py            # PPO 截断比率 (0.2)、策略熵系数与价值损失系数
│
├── widgets/                        # 专用模块化 UI 图元控件
│   ├── live_canvas_map_widget.py   # 高性能自绘画布，实时矢量渲染道路与信号灯头
│   ├── evp_vehicle_marker.py       # 特勤车辆专用画布渲染器（机构图元与警报脉冲光环）
│   ├── evp_vehicle_card.py         # 悬浮微观遥测探针卡片，展示瞬时 GPS、速度与 ETA
│   ├── planning_control_panel_widget.py # 规划工具栏、相位方案选择器与节点属性检查器
│   ├── mfd_viewer_widget.py        # 实时宏观基础图 (MFD) 动态拟合曲线图
│   ├── xai_viewer_widget.py        # Captum 神经网络特征敏感度归因分解图表
│   ├── street_info_widget.py       # 逐车道平均车速、占有率与排队长度实时数值读数
│   ├── traffic_light_widget.py     # 信号灯相位实时亮灯动画（红灯、黄灯、绿灯倒计时）
│   ├── audit_log_widget.py         # Guardian 安全否决司法取证审计日志表格
│   └── global_controls_widget.py   # 开始、暂停、单步步进与紧急人工接管覆盖按钮
│
├── renderers/                      # 画布矢量绘制与画面视觉平滑同步器
│   ├── map_drawer.py               # 车道与交叉口复杂几何多边形矢量光栅化器
│   ├── planning_map_renderer.py    # 拓扑节点与连通连线的视觉布局引擎
│   └── map_visual_syncer.py        # 60 FPS 流畅动画视觉状态同步器
│
└── locales/                        # 国际化多语言 (i18n) JSON 翻译字典
    ├── pt_br.json                  # 葡萄牙语（巴西） - 系统默认
    ├── en_us.json                  # 英语（美国）
    ├── es_es.json                  # 西班牙语
    ├── fr_fr.json                  # 法语
    ├── ru_ru.json                  # 俄语
    └── zh_cn.json                  # 简体中文
```

---

## 3. 路网规划视图与网络拓扑编辑器

**规划视图** ([`ui/views/planning_view.py`](../../ui/views/planning_view.py)) 为市政交通规划工程师提供了可视化交互检查与配置物理道路网络的平台：
- **拓扑干道编组：** 将物理相邻的交叉口群组划分为同一条协调干道，支持自动化绿波带配时参数整定。
- **相位与配时阶段检查：** 逐一校验最短绿灯安全约束、黄灯过渡时长与全红绿冲突保护间隔。
- **配置导出与下发：** 将优化后的信号时序方案直接导出至物理信号机配置库或标准的 CSV 批量模板。

有关矢量地图几何渲染的详细算法，请参阅 [矢量地图渲染与空间热力图](rendering_and_heatmaps.md)。

---

## 4. 系统托盘管理与单实例运行锁 (`SingleInstanceLock`)

CARINA 可作为系统后台高可靠服务平稳运行，并集成原生操作系统托盘图标：

### 4.1 系统托盘交互管理 ([`UITrayManager`](../../src/launcher/ui_tray_manager.py))
- **托盘菜单功能：** 最小化至托盘、唤起主仪表盘、查看实时终端日志、平滑重启服务、优雅终止系统。
- **系统原生通知弹窗：** 当微服务看门狗检测到子进程异常或 Guardian 触发紧急安全否决时，主动向操作系统桌面推送原生通知。

### 4.2 单实例 TCP 套接字互斥运行锁 ([`SingleInstanceLock`](../../src/launcher/single_instance.py))
- **绑定端口：** `42123`
- 当 CARINA 已在后台运行时，若操作员重复双击 `carina.py` 或打包后的二进制启动文件：
  1. 重复启动的子进程尝试绑定 TCP `42123` 端口失败。
  2. 捕捉到端口冲突异常后，向该端口发送 `RESTORE` 控制信号握手。
  3. 已在运行的系统主实例接收到该指令后，自动将主窗口弹出并置顶，重复进程优雅退出，杜绝重复实例争用硬件。

---

## 5. 模块化配置卡片架构 (`ui/cards/`)

CARINA 的参数配置总览大屏 ([`ui/views/settings_view.py`](../../ui/views/settings_view.py)) 遵循开闭原则（OCP），由 [`SettingsConfigurator`](../../ui/builders/settings_configurator.py) 动态组装：

| 配置卡片组件 | 业务功能覆盖范围 | 自动化 / 手动配置模式 |
| :--- | :--- | :--- |
| **`EVPFleetConnectionCard`** | 特勤应急车辆车队准入登记与 RFID/信标配置 | • 特勤机构标签分类 (警察、急救 SAMU、消防)<br>• 车牌号官方授权与未授权黑名单管理 |
| **`EVPSafetyParametersCard`** | 优先通行运动学门限、空间距离与安全清空参数 | • 街区准入判定门限 ($60\text{--}160\text{ m}$)<br>• 驶离注销门限 ($\le 15\text{ m}$)<br>• 最大驻留看门狗 ($45\text{ s}$)<br>• 法定黄灯及全红强制清空间隔 |
| **`RemoteGatewayCard`** | Go Web 网关与 Tailscale 虚拟网格穿透管理 | • 2201 端口 Web 网关守护进程启闭<br>• Tailscale Funnel 状态与 CCO 公网地址巡检 |
| **`AccountSettingsCard`** | 调度员身份认证与基于角色的权限控制 (RBAC) | • 角色划分 (管理员 Admin, 操作员 Operator, 审计员 Auditor)<br>• 会话安全与 JWT 令牌管理 |
| **`DatabaseSettingsCard`** | SQLite 与 PostgreSQL 持久化底层切换配置 | • 数据库引擎选型与连接池参数<br>• 连通性测试与自动化数据模式迁移 |
| **`PilotingSchoolCard`** | 智能体生命周期学习节奏与自主晋升准则 | • 基于路网规模的自动学习节奏计算<br>• 基于实测流体动力学的动态晋升裕度 ($\delta^*$) |
| **`RewardWeightsCard`** | 强化学习多目标物理平衡权重 (排队延误 vs 通行放行) | • 基于 HCM 行程时间 $\tau$ 的物理平衡计算<br>• 专家手动权重覆盖调整 |
| **`YellowScheduleCard`** | 低谷夜间时段黄闪自主定时排期调度计划 | • 时间窗口排期表 (HH:MM 起止时段)<br>• 交叉口选择性生效或全网应用开关 |
| **`AdvancedSystemCard`** | 系统底层 PBT 进化与看门狗高级参数 | • PBT 种群进化竞争百分位<br>• 看门狗启动宽限期与分析周期频率 |
| **`AdvancedDQNCard`** | Deep Q-Network 核心强化学习超参数 | • 经验回放缓冲区容量、目标网络同步周期、$\epsilon$ 探索衰减 |
| **`AdvancedPPOCard`** | PPO 战术策略优化核心超参数 | • 策略截断比率 ($\epsilon=0.2$)、策略熵奖励系数、价值网络损失权重 |
| **`TrafficRulesCard`** | 法定交通安全规范与信号配时底线门限 | • 最短绿灯时长、黄灯安全过渡、全红清空时距 |
| **`HardwareConnectionCard`** | 现场物理交通信号机通信集成 (NTCIP / UTMC) | • IP 端点、通信端口、SNMP 访问凭证与故障回退测试 |
| **`MonitorSettingsCard`** | 外部运营监控平台与异常告警流式推送 | • 本地 MQTT Broker / 云端 HTTP Webhook 遥测通道配置 |

---

## 6. EVP 视觉画布图元与实时遥测探针 (`ui/widgets/`)

在桌面端监控大屏中，CARINA 在 Flet 电子地图画布上实时矢量绘制执行紧急任务的特勤车辆：

- **`EVPVehicleMarker` ([`ui/widgets/evp_vehicle_marker.py`](../../ui/widgets/evp_vehicle_marker.py)):**
  - **机构专属矢量图元：** 依据车辆所属机构绘制鲜明的高辨识度几何标记：
    - *急救车 / SAMU：* 正等边三角形 ($\Delta$，白色 `#FFFFFF` / 警示红色 `#E53935`)。
    - *消防车 / Bombeiros：* 正方形 ($\square$，橙色 `#FF9800`/`#FF8C00` / 烈火红色 `#FF3D00`)。
    - *警察 / 军警：* 圆形 ($\bigcirc$，深蓝色 `#1E3A8A` / 皇家蓝 `#2563EB`)。
  - **警报闪烁动画：** 当 `siren_active=True` 时，图元周围以 $2.5\text{ Hz}$ 频率向外扩散同心光环脉冲，即刻向大屏值班调度员警示紧急出警状态。
  - **动态航向矢量：** 依据车载高精 GPS 航向角在线实时旋转图元朝向。

- **`EVPVehicleCard` ([`ui/widgets/evp_vehicle_card.py`](../../ui/widgets/evp_vehicle_card.py)):**
  - 悬浮在地图上方的 HUD 态势卡片，实时展示特勤呼号、当前瞬时车速（$\text{km/h}$）、警报鸣响状态、距离下游停止线距离（$\text{m}$）以及当前优先控制生命周期阶段（`APPROACHING` 接近、`HOLD_ACTIVE` 绿灯保持、`CLEARED` 驶离注销）。

---

## 7. 中央控制调度中心 (CCO) Web 与移动端全栈架构 (`src_tsx/src_cco`)

除了原生 Flet 桌面图形界面，CARINA 在 [`src_tsx/src_cco/`](../../src_tsx/src_cco) 目录内建了基于 **React 18**、**TypeScript**、**TailwindCSS** 与 **Vite** 构建的现代 Web 版**中央控制调度中心 (Central Control Operator, CCO)**。其源码全面遵循 **整洁架构（Clean Architecture）** 原则设计，确保了交通领域核心规则、底层流式通信与视图表现层的彻底解耦：

```text
src_tsx/src_cco/
├── domain/                         # 纯领域实体、模型与业务领域服务
│   ├── models/                     # 核心业务领域实体
│   │   ├── Topology.ts             # MapTopology、Node、Edge、Bounds 数据接口
│   │   ├── CongestionLevel.ts      # 拥堵指数领域值对象，解析饱和度颜色与阈值
│   │   ├── EmergencyVehicle.ts     # 应急车辆遥测与优先控制状态模型 (SAMU, 消防, 警察)
│   │   └── TrafficLight.ts         # 信号灯相位灯头、显示状态与倒计时模型
│   ├── services/                   # 纯几何计算与制图学领域服务
│   │   ├── MapProjectionService.ts # 等轴 2D 正交边界计算与 SVG 画布自适应纵横比
│   │   ├── GeoProjectionService.ts # 标准 WGS84 GPS 经纬度至 SUMO 笛卡尔坐标系的投影变换
│   │   └── StreetTopologyGrouperService.ts # 道路路段拓扑聚合与拥堵热力多边形生成
│   └── contracts/                  # 边界契约接口 (遵循依赖倒置原则 DIP)
│       ├── ITopologyRepository.ts  # 路网拓扑数据抓取协议契约
│       └── ICcoStreamService.ts    # 实时事件流与网络连接健康度接口
│
├── application/                    # 应用用例层与业务编排器
│   └── usecases/
│       ├── LoadTopologyUseCase.ts          # 加载并本地缓存城市路网几何结构
│       ├── ManageEmergencyFleetUseCase.ts   # 按特勤机构对车队分类并计算实时警报态
│       └── ProcessTelemetryUseCase.ts      # 解析 SSE 流式长连接数据包并映射至领域状态
│
├── infrastructure/                 # 外部适配器、API 与网关实现
│   ├── api/
│   │   └── HttpTopologyRepository.ts       # 基于 Axios/Fetch 实现的 ITopologyRepository
│   ├── stream/
│   │   └── SseCcoStreamService.ts          # 基于 SSE 的实时流客户端 (/cco/stream)，具备断线重连
│   └── adapters/
│       └── EChartsOptionAdapter.ts         # 将领域模型转换为 Apache ECharts 配置的适配器
│
└── presentation/                   # 响应式 UI 组件、自定义 Hooks 与主题样式
    ├── context/
    │   └── ThemeContext.tsx                # 值班作息主题切换器 (☀️ 日间明亮 / 🌙 夜间深色)
    ├── utils/
    │   └── haptics.ts                      # 面向移动平板触摸设备的触觉震动反馈工具
    ├── hooks/
    │   ├── useCcoViewModel.ts              # 根 ViewModel，统筹用例调度、SSE 数据流与 UI 状态
    │   ├── useCcoMapLayers.ts              # 缓存计算各个矢量图层（道路、节点、信号灯）
    │   └── useMapViewport.ts               # 平移、缩放、双指捏合手势与平滑飞越 (flyTo) 动画
    ├── components/
    │   ├── CcoHeader.tsx                   # 响应式紧凑顶栏，集成车队状态标牌、全局搜索与全屏
    │   ├── CcoMap.tsx                      # 高性能 SVG 矢量地图主画布，支持无级缩放
    │   ├── EvpAlertToast.tsx               # 悬浮应急优先警报横幅（移动端自适应为微胶囊）
    │   └── map/
    │       ├── InspectionBottomSheet.tsx   # 人机工效学移动端抽屉与桌面端巡检卡片
    │       ├── QuickSearchModal.tsx        # 全局快捷搜索与视角飞越定位 (Ctrl+K)
    │       ├── MapScaleBar.tsx             # 真实物理动态比例尺 (m/km)，精准标定 SUMO 坐标
    │       ├── MapRoadsLayer.tsx           # 道路路段双描边轮廓与拥堵热力图渲染图层
    │       ├── MapIntersectionsLayer.tsx   # 交互式交叉口节点图层，带大触控热区
    │       ├── MapTrafficLightsLayer.tsx   # 信号灯相位实时亮灯倒计时与光晕效果
    │       ├── MapEmergencyVehiclesLayer.tsx # 实时特勤车辆航向朝向、位移轨迹与警报光晕
    │       ├── MapGlowFilters.tsx          # 用于信号灯与警报图元的 SVG 霓虹滤镜定义
    │       ├── MapLegend.tsx               # 可折叠图例，展示车流饱和度颜色等级与图元符号
    │       └── MapZoomControls.tsx         # 地图缩放与相机快速回正控制器
    ├── styles/
    │   ├── flet_color_palette.json         # 与桌面端 Flet 界面 100% 精确对齐的色彩规范
    │   └── index.css                       # Tailwind 核心指令与移动端防过卷滚动锁定
    ├── App.tsx                             # 根组件，集成 ThemeProvider 与弹窗编排
    └── main.tsx                            # React DOM 应用主入口
```

---

## 8. 现代 CCO 前端交互与人机工效学特性

CCO 大屏前端无论是在交通指挥中心 4K 巨幕上展示，还是在现场巡检工程师的智能手机上操作，均能提供卓越的交互体验：

1. **移动端人机工程底部抽屉 (`InspectionBottomSheet.tsx`):**
   - 在移动设备（屏幕宽度 $< 768\text{px}$）上，要素详情卡片自动贴靠在屏幕底部，支持手势下拉关闭和拖拽展开。
   - 在桌面端工作站（$\ge 768\text{px}$）上，卡片悬浮停靠在屏幕边缘。
   - 提供全方位的微观诊断指标：
     - **应急特种车辆：** 呼号、当前速度（$\text{km/h}$）、GPS 航向角（$^\circ$）、警报状态以及目标路口。
     - **交通信号灯：** 信号灯 ID、当前放行相位、实时灯态（红/黄/绿）、地理坐标以及 F.E.N.I.X. 看门狗监管健康度。
     - **交叉口与道路：** 物理拓扑节点、道路名称、实时拥堵指数（$0\text{--}100\%$）以及通行服务水平。

2. **双重值班作息主题系统 (☀️ 白天 / 🌙 夜间):**
   - **地图日间模式 (`#F7F7F7`):** 高对比度明亮背景，适应白天户外或强光环境下巡检查阅。
   - **大屏夜间模式 (`#020617`):** 纯正深色背景，极大减轻夜班调度员长时间盯着大屏的视觉疲劳。
   - 支持通过顶栏按钮即时无缝切换，并持久化保存至浏览器 `localStorage`。

3. **快捷命令面板搜索与电影级视角飞越 (`QuickSearchModal.tsx` 与 `flyTo`):**
   - 支持通过顶栏搜索按钮或全局快捷键（`Ctrl+K` 或 `/`）快速呼出。
   - 毫秒级即时索引全城所有特勤车辆、信号机、交叉口及主干道路名称。
   - 选中任意目标后，触发基于三次缓动平滑插值的电影级视角飞越定位（`flyTo`），平滑将镜头移动至目标正中心并自动展开详情卡片。

4. **高精动态物理比例尺 (`MapScaleBar.tsx`):**
   - 实时根据当前视图缩放比例与 SUMO 仿真底图 1:1 的真实物理米制坐标，自动重标定物理动态比例尺（如 `|—— 100 m ——|`）。

5. **特勤车队互动过滤徽章:**
   - 顶栏的 **SAMU**（急救）、**Bombeiros**（消防）与 **Polícia**（警察）徽章支持点击联动交互。轻触特定机构即可高亮其所有在途车辆，其他车辆自适应半透明虚化。

6. **沉浸式全屏与移动端触觉震动反馈:**
   - 一键全屏切换，隐藏浏览器导航栏与边框，最大化展现地图画面。
   - 在支持震动的触摸设备上，与信号灯、特种车辆交互或点击缩放按钮时，调用 `navigator.vibrate` 提供细腻的微震动触觉反馈。

---

## 9. 高性能 Go Web 网关交付、CCO 优化与远程网络连接

Web 版 CCO 前端由高性能独立编译型 **Go 语言 Web 网关** ([`src_go/web_gateway/`](../../src_go/web_gateway)) 直接托管，监听 `2201` 端口（`CARINA_GATEWAY_PORT`）：

- **默认故障安全关闭与令牌保护交付：** 当处于禁用状态（`gateway_enabled=False`）时返回 `503 Service Unavailable`，启用后在 `/cco/` 路由提供经压缩的 React 静态资源，并通过恒定时间校验的 `CARINA_CCO_AUTH_TOKEN`、`CARINA_CCO_ALLOWED_ORIGIN` CORS 以及可选 HTTPS/TLS 保护 `/cco/stream`、`/cco/topology` 与 `/cco/broadcast`。
- **合成器线程与视口性能优化 (`src_tsx/src_cco/`)：** 采用仅触发 GPU 合成器的 CSS 关键帧动画（`transform` + `opacity`）、`useMapViewport.ts` 中由 `requestAnimationFrame` 引用驱动的平移缩放、`useCcoViewModel.ts` 中的浅比较状态差分计算，并在 `document.hidden` 为真时自动暂停车辆清理定时器。
- **低于 50ms 的 SSE 遥测实时流与证书固定推送：** 暴露 `/cco/stream` 端点，由 SDS [`CCOBroadcastClient`](../../src/sds/cco_broadcast_client.py) 供流（基于最新覆盖非阻塞发布与经由 `PinnedHTTPSConnection` 实现的 SHA-256 叶证书指纹固定）。
- **Tailscale 虚拟网格穿透：** 深度集成 Tailscale Funnel，使外场特勤车辆与市政交通指挥中心无需公网 IP 即可建立端到端加密的安全互联通道。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
