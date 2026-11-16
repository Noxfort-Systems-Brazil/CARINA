---
tags: [safety, guardian, watchdog, veto, failsafe, neuro-symbolic]
aliases: [安全机制架构, Guardian否决, 看门狗系统, 安全审计器]
---

# 🛡️ 安全架构、Guardian 防火墙与实时看门狗

本文档详尽规范了 CARINA 的双阶段神经符号安全防火墙（由 [`GuardianAgent`](../../src/agents/guardian_agent.py) 与 [`SafetyAuditor`](../../src/core/safety_auditor.py) 构成）、硬件故障安全（Fail-Safe）回退机制以及确定性实时微服务 [`Watchdog`](../../src/watchdog/watchdog_process.py) 进程。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🚨 查阅 [EVP 优先通行](evp_and_preemption.md) | 🚦 查阅 [硬件驱动程序](hardware_drivers.md) | 🧠 查阅 [神经理论推导](research_notes.md) | 🧪 查阅 [测试规范与质量保证](testing.md)

---

## 1. 双阶段安全防火墙机制全景

CARINA 实现了物理公共安全底线与深度强化学习算法探索性能的彻底解耦。深度神经网络策略可以自由提出动作建议，但所有动作在下发到底层物理信号机硬件之前，必须依次经过物理对数几率掩码与多阶段安全防火墙审查：

```text
状态 + PAE 潜向量 ──> [PhysicalActionMasker] ──> [ActionVetoResolver] ──> 硬件实际执行
                        (对数几率清空/最短绿)     ├── 0. EVP 优先权拦截 (SR-00)
                                                 ├── 1. 物理符号规则 (SR-01..SR-06)
                                                 └── 2. QR-D3QN + Noisy-OR 风险否决
```

- [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py)：在动作采样前约束 `ActorCriticNet` 的 FP32 原始对数几率（logits），严禁在黄灯/全红清空期间或低于最短绿灯时长时过早切相，并在达到最大绿灯上限时强制切换。
- [`ActionVetoResolver`](../../src/engine/action_veto_resolver.py)：在步进推理流水线中统一编排 EVP 优先通行覆盖（`SR-00`）与 `GuardianAgent` 溢流回堵否决（`ACTION_KEEP_STAGE`）。

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

## 3. 校准后的神经网络溢流回堵预测否决 (`GuardianAgent` & `src/safety/`)

**Guardian 守卫智能体** ([`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)) 将**分布式分位数回归对决双 Q 网络 (`D3QN_TCN`, `num_quantiles = 32`)** 与容量感知运动学物理模型及非补偿性风险融合机制深度集成：

- **尾部风险分位数估计 ($\text{CVaR}_{\alpha}$)：** `GuardianNeuralPredictor` 专门评估最坏情况下的下尾分位数（$\alpha = 0.20$），而非仅仅依赖均值 Q 值。
- **物理运动学与 PAE 估计 ([`GuardianPhysicsEstimator`](../../src/safety/guardian_physics_estimator.py))：** 严格截取驶入路段传感器三元组（`edge_feature_dim`），依据物理道路车辆容量（`edge_capacities`）对排队长度进行归一化，推演绿间隔清空视界 $H = \text{yellow} + \text{all\_red}$ 内的饱和度增长，并查询反事实 PAE 预测（针对 `ADVANCE` 与 `KEEP` 执行 `decode_with_uncertainty`）。
- **尺度不变校准与 Noisy-OR 融合 ([`GuardianRiskCalibrator`](../../src/safety/guardian_risk_calibrator.py))：** 在 `CHILD` 毕业时通过正则化逻辑回归与 $F_2$-score 阈值调优对分位数离散度进行校准，利用非补偿性 Noisy-OR（$1 - \prod_i (1 - c_i r_i)$）融合运动学、PAE 与 QR-D3QN 三路风险检测器，并设置硬性物理/PAE 溢流下限保障。
- **安全 `CHILD` 期影子训练与部署冻结 ([`GuardianShadowTrainer`](../../src/safety/guardian_shadow_trainer.py) & [`GuardianCheckpointService`](../../src/safety/guardian_checkpoint_service.py))：** 仅在 `Maturity.CHILD` 阶段（此时物理信号机仍由定周期方案控制）以离线策略（off-policy）训练 QR-D3QN；晋升至 `TEEN`/`ADULT` 时，执行 `finalize_child_calibration()` 与 `freeze_for_deployment()`（释放 `target_net`、`optimizer` 与 PER 缓冲区），并原子化持久化保存 `guardian_{tl_id}.pth`。

---

## 4. 实时微服务进程看门狗 (`src/watchdog/`)

`Watchdog` 独立微服务（由 [`src/watchdog/watchdog_process.py`](../../src/watchdog/watchdog_process.py) 与 [`src/watchdog/watchdog_logic.py`](../../src/watchdog/watchdog_logic.py) 驱动）以高精度时钟监控全部 8 个 CARINA 操作系统进程的健康心跳：

- **心跳上报周期：** 基于 `wd` IPC 队列，每 100 ms 上报一次心跳。
- **心跳超时熔断阈值：** 5.0 秒（系统启动初始宽限期：10 秒）。
- **确定性故障安全机制：** 一旦检测到 `AI_Process` 或 `CentralController` 发生异常崩溃、死锁或连续丢失心跳：
  1. 看门狗向桌面 UI 托盘管理器抛出高优先级致命警报。
  2. 通知 [`FailsafeManager`](../../src/controller/failsafe_manager.py) -> `HardwareGatewayCoordinator.on_failsafe_triggered()`，在 Go 网关上调用 `EmergencyReleaseControlAll()`（释放所有相位保持，同时保留 SNMP 驱动与 Trap 监听器就绪以便后续通过 `resume_control` 恢复控制）。
  3. 现场交通机瞬间无缝回退至本地固化定时配时方案或黄闪安全保底模式。
  4. 通过 `fenix` 队列及 [`fenix_supervision_loop.py`](../../src/launcher/fenix_supervision_loop.py) 触发 **F.E.N.I.X. 进程监管器** (`on_fenix_trigger`)，启动自主复活与闭环状态对账流程。
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

### 5.3 周期边界安全握手与零风险控制权交接 (`StateReconciler` & `FenixStageDispatcher`)
实现于 [`src/fenix/state_reconciler.py`](../../src/fenix/state_reconciler.py) 与 [`src/controller/fenix_stage_dispatcher.py`](../../src/controller/fenix_stage_dispatcher.py)：
- **周期中途插队风险：** 当 AI 进程重启重生时，若在物理信号机当前绿灯中途强行下发切相指令，极易违背绿间隔清空安全规范，引发急刹甚至碰撞事故。
- **闭环现场握手：** `FenixStageDispatcher` 从 Go 网关查询最新的现场控制器快照，借助 [`HardwareTelemetryDecoder`](../../src/drivers/hardware_telemetry_decoder.py) 解码当前活动相位，并通过 `fenix_post_resurrection` 对 `StateReconciler` 执行对账对齐（`reconcile_with_field`）。
- **自然边界释放权限：** 当现场物理控制器过渡至安全相位边界时解锁神经控制（`on_stage_transition_detected`），发出 `fenix_handover_complete` -> `HANDOVER_COMPLETE` 信号，从而使 `FenixSupervisor` 确认复活成功并恢复心跳控制（`resume_control`）。

---

有关现场控制器底层通信的具体细节，请参阅 [硬件驱动程序](hardware_drivers.md)。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
