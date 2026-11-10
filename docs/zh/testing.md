---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [测试指南, 单元测试, 安全模拟桩, 质量保证]
---

# 🧪 自动化测试规范、安全模拟与质量保证指南

CARINA 直接管控涉及公共人身安全的城市关键市政交通基础设施。在将任何代码变更部署至现场之前，绝对的高可靠性、确定性单元测试、交通机驱动模拟桩以及持续的安全性否决验证是强制性的红线要求。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🛠️ 查阅 [开发者指南](developer_guides.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 运行自动化测试套件 (`pytest`)

CARINA 拥有一套经过严密设计的自动化测试套件，内含 **861 个自动化测试用例**（已通过 `pytest --collect-only` 官方验证），确保系统各子系统的绝对安全、零缺陷回归与确定性微秒级故障切换。所有测试均位于 [`tests/`](../../tests) 目录。

### 1.1 执行全量自动化测试
```bash
pytest tests/ -v
```

### 1.2 生成代码测试覆盖率分析报告
精确评估针对 `src/` 核心源码的分支覆盖率与行覆盖率：
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
生成的 HTML 可视化覆盖率报告位于 `htmlcov/index.html`。

### 1.3 运行 Go 语言硬件网关单元测试 (`go test`)
运行原生 Go 单元测试套件，全面覆盖 NTCIP 1202、UTMC、SNMP 陷阱与设备自动发现：
```bash
cd src_go && go test -v ./...
```

---

## 2. 真实测试目录架构与模块清单

```text
tests/
├── conftest.py                     # 全局共享 pytest fixtures、临时数据库与模拟环境
├── mock_junctions.py               # 合成路网拓扑图与节点定义模拟桩
├── benchmark.py                    # 性能基准测试工具（吞吐量与时延抖动）
│
├── unit/                           # 隔离单元测试模块 (共 861 个自动化测试用例)
│   ├── test_evp_service.py         # EVPService 全生命周期、遥测摄入管线与优先通行触发
│   ├── test_evp_kinematics.py      # Haversine 测地距离、车速、航向角与街区准入门限
│   ├── test_evp_preemption_engine.py # 优先保持仲裁、45秒最大驻留看门狗与清空间隔
│   ├── test_evp_map_topology.py    # 拓扑匹配、汇入路段识别与目标优先相位映射
│   ├── test_evp_fleet_persistence.py # 官方认证车队 CRUD 事务与号牌缓存
│   ├── test_evp_config_repo.py     # EVP 参数配置仓储与判定阈值持久化
│   ├── test_evp_fleet_controller.py # 车队准入管理业务逻辑与表单验证
│   ├── test_evp_fleet_csv.py       # 特勤车队批量 CSV 导出与导入解析
│   ├── test_evp_fleet_save_flow.py # 车队 UI 录入至数据库提交的端到端数据流
│   ├── test_evp_hardware_parity_persistence.py # 跨数据库引擎的硬件状态一致性测试
│   ├── test_evp_settings_handler.py # EVP 参数在 settings.ini 与 .env 中的持久化
│   ├── test_evp_vehicle_marker.py  # Flet 画布特勤车辆图元符号与警报频闪动画
│   ├── test_local_agent.py         # PPO 战术智能体动作选择与策略更新循环
│   ├── test_guardian_agent.py      # D3QN 安全守卫智能体与溢流风险阈值校验
│   ├── test_strategist_agent.py    # ST-GATv2 Lite 图注意力干线绿波协同协调器
│   ├── test_settings_modular.py    # 模块化 SettingsService、Schema、提供者与 INI 读写
│   ├── test_settings_view.py       # Flet 设置视图与前端配置持久化测试
│   ├── test_monitor_client.py      # 多态 MonitorClient、HTTP 与 MQTT 传输通道
│   ├── test_monitor_disconnect.py  # 遥测重试机制、待发缓冲区刷写与优雅断连流
│   ├── test_core_components.py     # DecisionCoordinator 决策协调器与动作授权器测试
│   ├── test_go_gateway_bridge.py   # Go 硬件网关子进程与管道 IPC 桥接通信
│   ├── test_traffic_light_driver.py # 交通信号灯底层驱动抽象层测试
│   ├── test_traffic_modular_components.py # 交通灯模块化组件测试
│   ├── test_driver_factory_brand_model.py # 驱动工厂自动探测实例化 (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # SNMP Trap 陷阱监听器与硬件故障解析
│   ├── test_connection_db_persistence.py  # 交通机通信端点数据库持久化
│   ├── test_connection_manager_orchestrator.py # 硬件连接状态机编排测试
│   ├── test_fenix_supervisor.py    # FENIX 监管器生命周期、崩溃恢复与子进程重生
│   ├── test_fenix_process_runner.py # 子进程运行控制器 (SIGTERM / SIGKILL 优雅终止)
│   ├── test_fenix_recovery_policy.py # 滑动时间窗口崩溃恢复策略与指数退避
│   ├── test_fenix_state_reconciler.py # 周期边界安全握手与 FROZEN_SYNC 状态同步
│   ├── test_watchdog_fenix_integration.py # 看门狗超时熔断联动 FENIX 自动复活
│   ├── test_security_modular.py    # AuthService、UserService、PBKDF2 哈希与账户锁定
│   ├── test_security_manager.py    # 向后兼容的 SecurityManager 门面验证
│   ├── test_captum_analyzer.py     # Captum 积分梯度敏感度归因测试
│   ├── test_xai_report_builder.py  # ABNT 规范 Word 报告生成与原生 OMML 公式内嵌
│   ├── test_multi_agent_modular_builder.py # 多智能体模块化报告装配组装测试
│   ├── test_mfd_processor.py       # 宏观基础图 (MFD) 核心计算处理器
│   ├── test_mfd_report_generator.py # MFD 分析报告生成与宏观曲线拟合
│   ├── test_mfd_db_reconstruction.py # 从 PostgreSQL 数据库时序重构 MFD
│   ├── test_mfd_new_report.py      # MFD 全新报告自动化生产管线
│   ├── test_sas_report_generator.py # 智能分析系统 (SAS) 交通工程法定依据测试
│   ├── test_sas_data_transducer.py # SAS 遥测数据转换器
│   ├── test_sas_helpers.py         # SAS 交通工程数学公式辅助计算工具
│   ├── test_sas_mfd_db_cache.py    # SAS MFD 数据库缓存加速机制
│   ├── test_semantic_transducer_device.py # 离线端侧 SLM 语义转换器与显存自适应分配
│   ├── test_planning_view.py       # Flet 路网规划视图前端交互测试
│   ├── test_planning_architecture.py # 规划画布 Presenter 与配时方案导出处理器
│   ├── test_planning_export_handler.py # 信号配时方案 CSV 导出格式验证
│   ├── test_planning_panel_presenter.py # 规划面板交互 Presenter 测试
│   ├── test_live_canvas_map_widget.py # Flet 自绘画布道路与信号灯绘制测试
│   ├── test_map_interaction_precision.py # 缩放数学公式、坐标零漂移与路段点击拾取
│   ├── test_map_event_router_precision.py # 信号机灯头与道路路段点击事件精准消歧
│   ├── test_interactive_map_precision.py # 交互式地图触控精度与图层命中测试
│   ├── test_planning_map_sync.py   # PlanningMapRenderer 命中半径与画布同步
│   ├── test_live_data_provider_ipc.py # LiveDataProvider 内存 IPC 队列高速流式传输
│   ├── test_watchdog.py            # 看门狗心跳逻辑与各进程存活性时钟
│   ├── test_consolidation_purge.py # 流体动力学增量差分存储聚合整理与清理
│   ├── test_csv_template_export_import.py # 信号机通信端点 CSV 批量导入/导出
│   ├── test_db_schema_isolation.py # 测试执行期间的数据库模式隔离
│   ├── test_infrastructure_client.py # 交通基础设施设置依据客户端测试
│   ├── test_intersection_state_manager.py # 多路口相位状态协同跟踪管理器
│   ├── test_main_components.py     # 中央控制器主入口核心组件
│   ├── test_manual_override_hft.py # 高频人工紧急干预与相位强制覆盖
│   ├── test_pushdown_query.py      # 下推式 SQL 查询执行优化
│   ├── test_tls_state_provider.py  # 信号灯实时状态提供者
│   ├── test_ui_main_orchestrator.py # 主 UI 桌面编排测试
│   ├── test_window_manager.py      # 桌面端窗口全生命周期管理
│   ├── test_population_manager_pbt.py # 相位内 PBT 群体进化层级隔离与张量安全
│   ├── test_performance_margin_calculator.py # 流体动力学毕业晋升裕度计算与幼年遥测
│   ├── test_reward_weights_calculator.py # 物理奖励平衡计算器 (基于 HCM 路段行程时间)
│   ├── test_maturity_pacing_calculator.py # 基于路网物理拓扑规模的智能体训练节奏自适应
│   ├── test_yellow_schedule_manager.py # 夜间黄闪定时调度计划自动评估器
│   └── test_yellow_schedule_card.py # 黄闪配置卡片与时间窗口交互控件
│
└── integration/                    # 端到端系统级集成测试 (共 5 个大型集成模块)
    ├── test_system_integration.py    # gRPC 遥测摄入至控制动作下发的全链路闭环
    ├── test_gateway_ipc_pipeline.py  # Go 网关标准管道 NDJSON IPC 生产管线
    ├── test_hft_performance_sla.py   # 亚毫秒级高频循环响应延迟与 SLA 严格达标验证
    ├── test_postgres_migrations.py   # PostgreSQL Alembic 模式迁移与安全回滚
    └── test_watchdog_resilience.py   # 看门狗心跳超时故障安全熔断与 FENIX 自愈测试
```

---

## 3. 编写安全否决测试用例 (`SafetyAuditor`)

任何新增的动作控制策略或相位跳转逻辑，必须在 [`src/core/safety_auditor.py`](../../src/core/safety_auditor.py) 下通过严格的否决审查测试：

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """验证安全审计器严禁在最短绿灯时间未走完前提前切相。"""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # 模拟现场当前状态: 相位 1 仅仅点亮了 3.0 秒 (未满 7 秒)
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # 智能体企图提前强行切换至相位 2

    # 执行形式化安全审计
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # 强制维持当前放行相位 (ACTION_KEEP_PHASE)
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """验证规则 SR-00: 活动应急优先通行在确保黄灯清空的前提下，绝对优先锁定绿波走廊。"""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # RL 智能体提议切换至相位 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # 强制保持在 EVP 目标绿灯相位 1
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. 现场交通机硬件驱动模拟桩 (Mocking)

在离线开发且无物理信号机硬件的环境下进行集成测试时，可使用 [`tests/conftest.py`](../../tests/conftest.py) 中提供的 Mock Fixtures 模拟 UDP SNMP 的真实网络交互：

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
