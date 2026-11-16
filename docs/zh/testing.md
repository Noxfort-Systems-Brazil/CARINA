---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [测试指南, 单元测试, 安全模拟桩, 质量保证]
---

# 🧪 自动化测试规范、安全模拟与质量保证指南

CARINA 直接管控涉及公共人身安全的城市关键市政交通基础设施。在将任何代码变更部署至现场之前，绝对的高可靠性、确定性单元测试、交通机驱动模拟桩以及持续的安全性否决验证是强制性的红线要求。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🛠️ 查阅 [开发者指南](developer_guides.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 运行自动化测试套件 (`pytest`)

CARINA 拥有一套经过严密设计的自动化测试套件，内含 **967 个自动化 Python 测试用例**（已通过 `pytest --collect-only` 验证：分布在 192 个文件中的 **935 个单元测试**、8 个文件中的 **18 个集成测试** 以及 4 个根目录测试文件中的 **14 个测试**）外加分布在 15 个 `*_test.go` 文件中的 **46 个 Go 单元测试**，确保系统各子系统的绝对安全、零缺陷回归与确定性微秒级故障切换。所有测试均位于 [`tests/`](../../tests) 与 [`src_go/`](../../src_go) 目录。

### 1.1 使用内存防护运行测试 (`scripts/pytest_limited.sh`)
为防止多进程 PyTorch/SLM 测试固件在全量测试期间耗尽宿主机内存，请优先使用内核限制运行脚本 [`scripts/pytest_limited.sh`](../../scripts/pytest_limited.sh) 并配合 [`tests/memory_guard.py`](../../tests/memory_guard.py)：
```bash
# 强制执行 systemd cgroup v2 内存上限 (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# 或回退至 ulimit -d + CARINA_PYTEST_MAX_RAM_MB 进程树 RSS 守护：
./scripts/pytest_limited.sh tests/ -v
```
- **确定性资源回收：** `tests/memory_guard.py` 采样进程树 RSS，执行软性 `gc.collect()` / `malloc_trim()`，并通过 `reclaim_test_resources()` 清理单例实例（`GoGatewayClient`、`HardwareConnectionManager`、`DatabaseManager`、Matplotlib 图形对象）。
- **离线 SLM 测试防护：** 在 `pytest` 执行期间默认禁用真实 GGUF LLM 加载，除非显式导出 `CARINA_ALLOW_REAL_SLM=1`。

### 1.2 直接执行全量测试与生成覆盖率报告
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
生成的 HTML 可视化覆盖率报告位于 `htmlcov/index.html`。

### 1.3 运行 Go 语言硬件网关单元测试 (`go test`)
运行原生 Go 单元测试套件（共 46 个测试函数，全面覆盖 NTCIP、UTMC、SNMPv3/codec、二进制 Trap、设备自动发现、故障安全、EVP 与 Web 网关认证/TLS）：
```bash
cd src_go && go test -v -race ./...
```

---

## 2. 真实测试目录架构与模块清单

```text
tests/
├── conftest.py                     # 全局共享 pytest fixtures、临时数据库与模拟环境
├── memory_guard.py                 # 进程树 RSS 监控、软性 GC 裁剪与单例资源回收
├── mock_junctions.py               # 合成路网拓扑图与节点定义模拟桩
├── benchmark.py                    # 性能基准测试工具（吞吐量与时延抖动）
├── test_*.py                       # 4 个根目录测试套件（14 个测试：基本健康检查、不变量、节律、全周覆盖率）
│
├── unit/                           # 隔离单元测试模块 (192 个文件 / 共 935 个已收集测试)
│   ├── test_closed_loop_hardware_control.py # NTCIP/UTMC 位掩码解码与闭环相位同步
│   ├── test_field_readiness_configs.py # 单路口 config_path、令牌转发与相位定时配置
│   ├── test_grpc_security.py       # Synapse gRPC TLS/mTLS 与 BearerTokenServerInterceptor 测试
│   ├── test_sds_cco_broadcast_security.py # CCOBroadcastClient TLS + SHA-256 叶证书指纹固定
│   ├── test_guardian_calibration_and_training.py # QR-D3QN CHILD 训练、F2 校准、Noisy-OR 与冻结
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool、SQLite WAL 编译指示与 db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE、torch.vmap、NumPy GAE、主机 ReplayMemory
│   ├── test_phase2_db_ipc_optimizations.py # make_interval SQL、ThreadSafePipeConnection 与 EVP 保留策略
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock、pynvml 显存、mpl_utils、XAI 缓存
│   ├── test_phase4_gateway_evp_ui_optimizations.py # MapAnimator 窗口暂停、AuditLog 分页、CCO 性能
│   ├── test_pytest_memory_guard.py # 进程树 RSS 采样、软性裁剪与资源回收测试
│   ├── test_solid_full_audit_refactoring.py # 隔离接口与 SOLID 协调器重构测试
│   ├── test_solid_gateway_and_step_refactoring.py # 网关协调器与步进管线 DIP 依赖倒置测试
│   ├── test_evp_*.py               # 12 个 EVP 模块（服务、运动学、优先通行、车队、UI 图元标记）
│   ├── test_local_agent.py         # PPO 战术智能体动作选择与策略更新循环
│   ├── test_guardian_agent.py      # D3QN 安全守卫智能体与溢流风险阈值校验
│   ├── test_strategist_agent.py    # ST-GATv2 Lite 图注意力干线绿波协同协调器
│   ├── test_pae_model.py           # 动作条件 iTransformer PAE 与不确定性测试
│   ├── test_remote_gateway_and_cco.py # Tailscale Web 网关与 CCO 流测试
│   ├── test_settings_modular.py    # 模块化 SettingsService、Schema、提供者与 INI 读写
│   ├── test_monitor_client.py      # 多态 MonitorClient、HTTP 与 MQTT 传输通道
│   ├── test_go_gateway_bridge.py   # Go 硬件网关子进程与管道 IPC 桥接通信
│   ├── test_fenix_*.py             # FENIX 监管器、运行器、恢复策略与状态对齐器
│   ├── security/                   # 密码学、PBKDF2、密码策略与 SOLID 安全测试套件
│   └── ...                         # 全面覆盖 core、mfd、sas、xai、rendering 与 ui
│
└── integration/                    # 端到端系统级集成测试 (8 个模块 / 18 个测试)
    ├── test_system_integration.py    # gRPC 遥测摄入至控制动作下发的全链路闭环
    ├── test_gateway_ipc_pipeline.py  # Go 网关标准管道 NDJSON IPC 生产管线
    ├── test_gateway_ownership_and_fenix_roundtrip.py # CARINA_GATEWAY_ROLE owner/remote 与 FENIX 往返测试
    ├── test_go_gateway_snmp_hil_loopback.py # 真实编译 Go 二进制文件 <-> SNMP 模拟代理硬件在环回环
    ├── test_hft_performance_sla.py   # 亚毫秒级高频循环响应延迟与 SLA 严格达标验证
    ├── test_postgres_migrations.py   # PostgreSQL Alembic 模式迁移与安全回滚
    ├── test_traffic_light_drivers.py # 高层 NTCIP/UTMC 驱动集成校验
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
