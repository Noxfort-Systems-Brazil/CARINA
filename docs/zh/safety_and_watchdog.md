---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [安全机制架构, Guardian否决, 看门狗系统, 安全审计器]
---

# 🛡️ 安全架构、Guardian 防火墙与实时看门狗

本文档详尽规范了 CARINA 的双阶段神经符号安全防火墙（由 [`GuardianAgent`](../../src/agents/guardian_agent.py) 与 [`SafetyAuditor`](../../src/core/safety_auditor.py) 构成）、硬件故障安全（Fail-Safe）回退机制以及确定性实时微服务 [`Watchdog`](../../src/watchdog/watchdog_process.py) 进程。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🚨 查阅 [EVP 优先通行](evp_and_preemption.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🧠 查阅 [神经理论推导](research_notes.md) | 🧪 查阅 [测试规范与质量保证](testing.md)

---

## 1. 双阶段安全防火墙机制全景

CARINA 实现了物理公共安全底线与深度强化学习算法探索性能的彻底解耦。深度神经网络策略可以自由提出动作建议，但所有动作指令在下发到底层物理信号机硬件之前，必须通过严格的确定性安全防火墙双重形式化审查：

```text
提议相位动作 ──> [0. EVP 优先权拦截] ──> [1. 物理符号规则] ──> [2. 神经网络否决] ──> 硬件实际执行
                        │                           │                    │
                        ├── 全绿波应急走廊 (HOLD)    ├── 最短绿灯 / 黄灯  └── 溢流回堵风险 (Q > 0.8)
                        └── 强制安全清空间隔校验    └── 绿冲突位矩阵否决 └── 紧急排队消散相位
```

---

## 2. 形式化符号否决规则清单 (`SafetyAuditor`)

位于核心层的 [`SafetyAuditor`](../../src/core/safety_auditor.py) 与 [`GuardianSymbolicAuditor`](../../src/safety/guardian_symbolic_auditor.py) 强制执行绝对硬性物理约束，任何神经网络优化器均不可松弛、不可修改、亦不可旁路逾越：

| 规则编号 | 规则名称 | 物理约束语义说明 | 触发违规时的强制动作 |
| :--- | :--- | :--- | :--- |
| **SR-00** | **应急车辆优先 (EVP)** | 检测到在编特种应急车辆（SAMU急救/消防/警车）鸣响警报接近路口。 | 优先拦截提议动作；强制执行法定黄灯及全红清空，并在目标绿波走廊注入 `ACTION_HOLD` 保持。 |
| **SR-01** | **最短绿灯时长 (Min Green)** | 当前放行相位绿灯持续时长严禁低于 $T_{min} = 7.0\text{ s}$，保障排队车辆正常起步。 | 强制维持当前相位 `ACTION_KEEP_PHASE`。 |
| **SR-02** | **黄灯清空过渡 (Yellow)** | 任何相位切换必须强制插入持续时长不低于 $3.0\text{ s}$ 的黄灯过渡警示间隔。 | 拦截跳相指令，强制插入黄灯过渡时序。 |
| **SR-03** | **全红清空时距 (All-Red)** | 存在冲突转向车流的相位切换时，必须强制插入 $2.0\text{ s}$ 的全红空间清空间隔。 | 强制执行全红清空状态。 |
| **SR-04** | **最短红灯时长 (Min Red)** | 未被放行的转向车流在被再次唤醒前，必须满足设定的最短红灯间隔。 | 抑制相位的过早重新激活。 |
| **SR-05** | **最大绿灯上限 (Anti-Starvation)** | 当冲突进口道存在排队等待车辆时，当前相位绿灯持续时间不得超过最大绿灯上限。 | 强制结束当前相位并切换至有排队需求的相交方向。 |
| **SR-06** | **冲突矩阵与幽灵绿灯 (Ghost Green)** | 严禁对冲突车流同时放行绿灯，或在完全无流量的空进口道上点亮幽灵绿灯。 | 硬性绝对否决，立即回退至预设安全驻留相位。 |

---

## 3. 神经网络溢流回堵预测否决 (`GuardianAgent`)

**Guardian 守卫智能体** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) 运行基于 TCN 时序特征提取的 Dueling Deep Q-Network，实时预测干道**溢流回堵风险指数** ($Q_{risk} \in [0.0, 1.0]$)：

- **风险安全阈值 ($\tau_{risk}$):** $0.80$（可于 `config/settings.ini` 动态配置）。
- **紧急干预接管：** 若 $Q(s, a_{proposed}) > 0.80$，本地战术智能体的提议动作将被立即否决。Guardian 智能体将强行注入紧急消散相位，在上游车流网状锁死前快速放行过饱和进口道车流。

---

## 4. 实时微服务进程看门狗 (`src/watchdog/`)

`Watchdog` 独立微服务（由 [`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) 与 [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py) 驱动）以高精度时钟监控全部 8 个 CARINA 操作系统进程的健康心跳：

- **心跳上报周期：** 基于 `wd` IPC 队列，每 100 ms 上报一次心跳。
- **心跳超时熔断阈值：** 5.0 秒（系统启动初始宽限期：10 秒）。
- **确定性故障安全机制：** 一旦检测到 `AI_Process` 或 `CentralController` 发生异常崩溃、死锁或连续丢失心跳：
  1. 看门狗向桌面 UI 托盘管理器抛出高优先级致命警报。
  2. 立即通知 [`FailsafeManager`](../../src/controller/failsafe_manager.py) 主动撤销现场物理控制器上的所有远程相位保持锁。
  3. 现场交通机瞬间无缝回退至本地固化定时配时方案或黄闪安全保底模式。
  4. 触发 **F.E.N.I.X. 进程监管器** (`on_fenix_trigger`) 启动自主复活与状态安全对齐流程。
  5. **优先驻留看门狗：** 与此同时，[`EVPPreemptionEngine`](../../src/evp/evp_preemption_engine.py) 强制执行 $45.0\text{ s}$ 最大优先绿灯驻留时限，若车载终端驶离信号丢失或延迟，强制释放干道锁定。

---

## 5. F.E.N.I.X. 自愈与崩溃恢复子系统架构 (`src/fenix/`)

为实现 7×24 小时高可靠连续运行且彻底杜绝人工现场干预，CARINA 在 [`src/fenix/`](../../src/fenix) 实现了 **F.E.N.I.X.**（Fault-tolerant Engine for Networked Intelligent eXecution，网络化智能执行容错引擎）。

```text
       Watchdog 心跳超时 / 子进程崩溃
                     │
                     ▼
          ┌─────────────────────┐
          │   FenixSupervisor   │ (自愈编排门面服务)
          └──────────┬──────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐     ┌──────────────────────┐
│  RecoveryPolicy  │     │   SubprocessRunner   │
│ (滑动窗口指数退避)│     │(优雅 SIGTERM -> KILL)│
└──────────────────┘     └──────────┬───────────┘
                                    │ 重新派生子进程
                                    ▼
                         ┌──────────────────────┐
                         │   StateReconciler    │
                         │ (FROZEN_SYNC 冻结同步)│
                         └──────────┬───────────┘
                                    │ 观测至下一个自然过渡边界 (零绿冲突风险)
                                    ▼
                         ┌──────────────────────┐
                         │    NORMAL (完全接管) │
                         └──────────────────────┘
```

### 5.1 F.E.N.I.X. 生命周期状态机 (`FenixState`)
定义于 [`src/fenix/protocols.py`](../../src/fenix/protocols.py)：
- **`IDLE`**：子进程监管启动前的初始就绪态。
- **`NORMAL`**：受管 AI 推理引擎运行平稳，具备完整的实时物理控制权。
- **`SUSPECT`**：看门狗检测到心跳丢失或遥测数据异常波动。
- **`RESTARTING`**：僵尸/异常进程已被终止；正在退避冷却窗口等待重新派生。
- **`FROZEN_SYNC`**：新生子进程已正常摄入实时路况遥测，但推理与控制指令处于严格物理锁定状态（`is_inference_allowed = False`）。
- **`SHADOW_WARMUP`**：后台影子前向推理计算，预热 PyTorch 算子缓存与 GATv2 图节点嵌入。
- **`HANDOVER_PENDING`**：等待现场物理交通机自然过渡至下一个安全周期边界。
- **`FAILSAFE_ACTIVE`**：恢复期间现场交通机执行本地自主定时保底方案的降级态。
- **`HALTED`**：滑动窗口内崩溃次数超出最大配额熔断阈值；系统锁定于安全保底模式并向人工发出调度警报。

### 5.2 滑动窗口崩溃恢复策略 (`WindowedCrashRecoveryPolicy`)
实现于 [`src/fenix/recovery_policy.py`](../../src/fenix/recovery_policy.py)：
- 在滑动时间窗口（默认：$300\text{ s}$）内精确追踪子进程崩溃频率。
- 在重启尝试之间按指数阶梯计算冷却退避时间（$2.0\text{ s} \to 4.0\text{ s} \to 8.0\text{ s}$）。
- 遏制死循环雪崩重启：若崩溃频次超过 $M$ 次阈值（默认：5 次），系统立即熔断置为 `HALTED`。

### 5.3 周期边界安全握手与零风险控制权交接 (`StateReconciler`)
实现于 [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py)：
- **周期中途插队风险：** 当 AI 进程重启重生时，若在物理信号机当前绿灯中途强行下发切相指令，极易违背绿间隔清空安全规范，引发急刹甚至碰撞事故。
- **零风险对齐握手：** 状态对齐器主动轮询现场控制器瞬时放行相位状态（`reconcile_with_field`）。
- **自然边界释放权限：** 仅当现场物理控制器根据自身本地计划自然走完当前相位并切换至下一相位边界时（`on_stage_transition_detected`），才正式解除控制锁定，确保平滑、无冲突地接管物理路口。

---

有关现场控制器底层通信的具体细节，请参阅 [硬件驱动程序](hardware_drivers.md)。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
