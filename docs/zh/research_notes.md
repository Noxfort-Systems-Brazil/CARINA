---
tags: [research, ai, math, neural]
aliases: [神经科学研究, 数学理论推导, PPO-TCN, GOMES]
---

# 🧠 神经网络前沿研究与数学理论推导

本文档详尽规范了支撑 CARINA **基于图的大规模多智能体专家运行系统 (GOMES)** 以及 **DA SILVA** 智能体渐进成熟度课程学习机制的数学理论框架、神经网络架构与优化推导。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🏛️ 查阅 [多进程架构](architecture.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🔍 查阅 [可解释人工智能与SAS](xai_and_sas.md)

---

## 1. PPO-TCN：统一因果时序卷积网络与向量化推理

传统循环神经网络（如 LSTM/GRU）在长回合的时间反向传播（BPTT）过程中极易遭遇梯度消失与序贯计算瓶颈。CARINA 采用跨战术、安全与战略智能体共享的**统一因果时序卷积网络（TCN）主干**（[`src/models/tcn_backbone.py`](../../src/models/tcn_backbone.py)）彻底替代 LSTM：

```text
输入历史张量: X ∈ ℝ^(B × T × C) -> 转置为 (B × C × T)
  B: 训练批量大小（或在 torch.vmap 下的路网车队规模）
  C: 每个时间步的特征维度（时间占有率、平均车速、排队长度、信号灯相位、ped_calls + PAE 潜向量）
  T: 时序历史上下文滑动窗口（默认 sequence_length = 12 帧）
```

### 1.1 空洞因果卷积、`GroupNorm` 与注意力池化

为了严格杜绝未来信息的时序泄漏（即时间步 $t$ 处的特征推断严格仅依赖于 $\le t$ 的历史观测），同时保持与 `torch.vmap` 及 `torch.compile` 的完全兼容，`TemporalBlock` 以 `TemporalConv1d`、因果通道级 `GroupNorm(1, C)`、`SiLU`、正交初始化及 [`TemporalAttentionPool`](../../src/models/tcn_backbone.py) 替代了已弃用的 `weight_norm`：

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

其中各项定义如下：
- $k$：一维卷积核尺寸 ($k = 3$)
- $d$：空洞扩张因子 ($d = 2^l$，在 `num_levels = 3` 的层级索引 $l \in \{0, 1, 2\}$ 处呈指数级扩张)
- 感受野有效跨度：$RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

[`ActorCriticNet`](../../src/models/actor_critic_tcn.py) 在 `TemporalAttentionPool` 之上构建解耦的 Actor 与 Critic 主干，输出原始 FP32 对数几率（`n_actions = 2`：`0 = ADVANCE`，`1 = KEEP`），并直接经由 [`PhysicalActionMasker`](../../src/engine/physical_action_masker.py)（`apply_action_mask`）屏蔽非法动作以支持 AMP 安全的 `Categorical(logits=...)` 采样。面向同构交叉口，[`FleetBatchInferencer`](../../src/engine/fleet_batch_inferencer.py) 利用 `torch.func.stack_module_state` + `torch.vmap` 执行批量化策略推理。

### 1.2 PPO 截断代理目标函数与主机端 NumPy GAE

PPO 策略网络利用由 [`PPOOptimizer`](../../src/optimizer/ppo_optimizer.py) 在主机端 NumPy 中计算的广义优势估计（GAE）优化截断代理目标函数，并在 `k_epochs` 个小批次（minibatch）间复用 `precomputed_latents`：

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

其中：
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ 代表新旧策略的动作概率比率。
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ 代表 GAE 广义优势估计量。
- $\epsilon = 0.2$ 代表策略概率更新的截断保护边界。

---

## 2. 通用动作条件 iTransformer 世界模型 (PAE)

**预测自编码器 (Predictive Autoencoder, PAE)**（[`src/models/pae.py`](../../src/models/pae.py)）是一个共享的**动作条件 iTransformer 世界模型**，用于从历史状态序列推演未来车道交通动力学演化及认知不确定性：

```text
X_hist [B, T, D_in] ──> 逐变量 RevIN + [mean, std] 统计量嵌入
                                 │
                                 ▼ (跨 D_in 变量的倒置注意力 + key_padding_mask)
                         iTransformer 编码器 + 交叉注意力潜查询 (Z ∈ ℝ^latent_dim)
                                 │
                                 ├──> 拼接注入 LocalAgent 与 GuardianAgent 状态向量
                                 └──> + 动作嵌入 (0=ADVANCE, 1=KEEP) ──> (mean, log_var)
```

### 2.1 核心架构机制
- **逐变量 RevIN 与键填充掩码 (`pae_preprocessing.py`)：** 通过可逆实例归一化（Reversible Instance Normalization）将时序动态与静态路段饱和尺度解耦，并在交叉注意力池化期间对零填充维度（`valid_dims`）施加掩码，确保驶入道路数量较少的路口不会污染潜向量表征。
- **反事实动作条件化与异方差不确定性：** `decode_with_uncertainty(z, action)` 针对 `0 = ADVANCE` 与 `1 = KEEP` 分别预测期望下一时刻状态 $\hat{\mu}(z, a)$ 及其对数方差 $\log \hat{\sigma}^2(z, a)$。
- **单遍车队批量编码 (`BatchedPAEEncoder`)：** 在每个仿真步对所有活动路口执行一次性统一编码，并支持通过 `torch.compile`（`torch_compile_helper.py`）编译加速子模块。

---

## 3. 分布式 QR-D3QN 守卫安全智能体与 Noisy-OR 校准

**Guardian 守卫智能体**（[`src/agents/guardian_agent.py`](../../src/agents/guardian_agent.py)，[`src/models/d3qn_tcn.py`](../../src/models/d3qn_tcn.py)）将**分布式分位数回归对决双 Q 网络 (`QR-D3QN`, `num_quantiles = 32`)** 与容量感知运动学推演及校准后的非补偿性传感器融合机制（`src/safety/`）深度结合：

$$Z_\tau(s, a) = V_\tau(s) + \left( A_\tau(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A_\tau(s, a') \right), \quad \tau_k = \frac{k + 0.5}{N}, \; N=32$$

- **尾部风险 ($\text{CVaR}_{\alpha}$)：** 基于 `forward_quantiles` 评估下尾条件风险价值（$\alpha = 0.20$），而非仅依据均值期望做判断。
- **容量归一化运动学推演 (`GuardianPhysicsEstimator`)：** 严格截取驶入路段三元组（`edge_feature_dim`），依据物理道路车辆容量（`edge_capacities`）对排队长度进行归一化，推演绿间隔清空视界 $H = \text{yellow} + \text{all\_red}$ 内的饱和度演化，并计算由动态 PAE 可靠度（$\exp(-\text{MSE}/0.10)\exp(-\overline{\log \sigma^2}/2)$）加权的反事实 PAE UCB 溢流风险。
- **尺度不变校准与 Noisy-OR 融合 (`GuardianRiskCalibrator`)：** 在 `CHILD` 毕业时拟合正则化逻辑回归校准参数与 $F_2$-score 决策阈值，通过非补偿性 Noisy-OR 融合运动学（$r_{\text{kin}}$）、PAE（$r_{\text{pae}}$）与神经网络（$r_{\text{d3qn}}$）三路检测器：
  $$P_{\text{spillback}} = 1 - (1 - r_{\text{kin}})(1 - c_{\text{pae}} r_{\text{pae}})(1 - c_{\text{d3qn}} r_{\text{d3qn}})$$
- **`CHILD` 期影子训练与部署冻结 (`GuardianShadowTrainer`)：** 在 `Maturity.CHILD` 阶段由固定配时计划控制现场硬件的同时开展安全的离线策略学习，晋升毕业时执行 `freeze_for_deployment()`（释放 `target_net`、`optimizer` 与 PER 缓冲区）并持久化保存 `guardian_{tl_id}.pth`。

---

## 4. 宏观战略协调层：支持在线预测与 CTDE 的 ST-GATv2 Lite (`src/models/st_gatv2_lite.py`)

为了在主干道相邻路口之间自主协调形成大范围“动态绿波带”，CARINA 将整座城市的道路拓扑建模为有向图 $\mathcal{G} = (\mathcal{V}, \mathcal{E})$，采用 `TemporalConvNetLite` + `TemporalAttentionPool` 后接两层残差 `GATv2Conv` 层，并配备辅助单步前向预测头（`pred_head`）和协同 CTDE 评价头（`global_critic_head`）。[`StrategicCoordinator`](../../src/engine/strategic_coordinator.py) 通过无副作用的 [`StateExtractor.peek_state()`](../../src/engine/state_extractor.py) 采集节点序列。

### 4.1 GATv2 动态注意力系数计算

针对物理连通的相邻交叉口节点 $i, j \in \mathcal{V}$，GATv2 在线计算动态空间注意力权重 $\alpha_{ij}$：

$$\alpha_{ij} = \frac{\exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_j] \right) \right)}{\sum_{k \in \mathcal{N}_i} \exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_k] \right) \right)}$$

其中：
- $h_i, h_j$：路口节点 $i$ 与其邻居节点 $j$ 的高维嵌入特征。
- $\mathbf{W}$：全局共享的线性变换参数矩阵。
- $\mathbf{a}$：可学习的空间注意力权重向量。

---

## 5. DA SILVA 智能体演化与成熟度课程体系

**自主性验证动态智能体安全集成学习课程体系（DA SILVA）** 引入**策略香农熵（Policy Shannon Entropy）** 作为评估智能体策略成熟度的核心数学测度：

$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_{a \in \mathcal{A}} \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

### 5.1 晋升评估准则与动态熵衰减边界

为彻底杜绝盲目随机探索策略过早获得硬件控制权，系统设定了动作空间理论最大熵上限 $E_{max} = \ln(|\mathcal{A}|)$（在 `DynamicEntropyCalculator` 中，针对 CARINA 的二元 `ADVANCE`/`KEEP` 动作空间默认设为 $E_{max} = \ln(2) \approx 0.6931$），或归一化熵 $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$。`DynamicEntropyCalculator` 依据训练经历的迭代回合数（$t$ 回合）动态衰减准入熵阈值：

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

其中，理想目标熵 $E_{ideal} = 0.10$。幼年 $\to$ 青年阶段衰减系数取 $k = 0.05$，青年 $\to$ 成年阶段衰减系数取 $k = 0.15$。渐进的目标晋升区间如下：

1. **幼年期 CHILD（影子观察模式）：** $\mathcal{H} > E_{child}(t)$（渐进基准 $\mathcal{H} > 0.40$）。动作仅作影子推演（仅被动采集遥测）；底层由传统固定配时控制现场信号机，同时 `GuardianShadowTrainer` 安全地以离线策略（off-policy）训练 QR-D3QN。由于对所有 $t \ge 1$ 均满足 $E(t) < \ln(2)$，均匀随机策略（$\mathcal{H} = \ln 2$）绝对无法跨级晋升。不可逾越的法定安全观测底线：整整 1 周（通过 [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py) 动态计算求得的 $E_{\text{week}}$ 回合），确保覆盖完整的 168 个真实小时日历时段。
2. **青年期 TEEN（限制性自主运行）：** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$（渐进区间 $0.15 < \mathcal{H} \le 0.40$）。智能体仅获准在非高峰时段尝试驱动物理硬件（依据 Synapse 动态排程或经典城市通行标准）；在早晚高峰时段，系统强制降级为影子模式以确保道路交通安全。不可逾越的法定安全观测底线：整整 1 周（$E_{\text{week}}$ 回合）。
3. **成年期 ADULT（完全自主接管）：** $\mathcal{H} \le E_{adult}(t)$（渐进基准 $\mathcal{H} \le 0.15$，在 $k=0.15$ 下经历 $t \ge 20$ 回合达成）且强化学习平均奖励 $\mu_{reward} > \mu_{baseline} + \delta^*$。正式授予 7×24 小时全天候、全工况物理硬件自主控制权限。

### 5.1.1 基于路网拓扑的回合步数动态缩放与单周节律
为彻底摒弃武断的人工经验“魔法数字”，使每个训练回合的观察视界与城市路网的物理时空尺度精确对齐，CARINA 引入 [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py)：
- **拓扑复杂度 ($C_{\text{topo}}$)：** 实际物理道路连接数 $E_{\text{real}}$（将往返双向合并为同一物理路段，并剔除带 `:` 的交叉口内部微连接）与信号灯总数 $N$ 之比，按全网平均车道数 $\bar{F}$ 赋予弹性权重：
  $$C_{\text{topo}} = \text{clamp}\left( \frac{E_{\text{real}}}{N} \times \left(1.0 + 0.1 \times (\bar{F} - 1.0)\right), \quad 0.8, \quad 1.6 \right)$$
- **次线性物理松弛耗时：** 避免特大城市路网规模爆炸导致训练回合时长失控，依据关键走廊深度 ($\sqrt{N}$) 和地理跨度直径 ($D_{\text{km}}$) 进行次线性平滑：
  $$T_{\text{physical}} = 180 + \left( 60 \cdot \sqrt{N} + 30 \cdot D_{\text{km}} \right) \times C_{\text{topo}}$$
- **单回合决策步数 ($S$)：** 以悲观控制采样周期 $\Delta t = 250\text{ ms}$（$4\text{ 步/秒}$）进行量化，按 100 步为基底向上取整，并严格限制在 2.5 分钟（$600\text{ 步}$）至 1 小时（$14\,400\text{ 步}$）区间：
  $$S = \text{clamp}\left( \left\lceil \frac{T_{\text{physical}} / 0.25}{100} \right\rceil \times 100, \quad 600, \quad 14400 \right)$$
- **不可逾越的 1 周安全底线回合数 ($E_{\text{week}}$)：** 完整观测 7 天连续日历周期（$604\,800\text{ 秒}$）所需的最少训练回合数：
  $$E_{\text{week}} = \left\lceil \frac{604800}{S \times 0.25} \right\rceil$$

### 5.1.2 完整周日历覆盖率追踪与抗重启持久化
为确保策略在晋升前充分历经真实城市路况的全谱系考验（工作日、深夜低谷、早晚高峰及周末假日），[`WeeklyCoverageTracker`](../../src/core/weekly_coverage_tracker.py) 与 [`ActionAuthorizer`](../../src/core/action_authorizer.py) 协同运作：
- **168 小时日历时空矩阵：** 精确映射每周 168 个独立小时槽位（$7\text{ 天} \times 24\text{ 小时}$）。每帧附带真实时间戳（`datetime.fromtimestamp(raw_timestamp)`）的数据均打卡登记至 `(星期几, 小时)` 矩阵单元。
- **原子化文件持久化：** 覆盖进度原子写入持久化存储（`weekly_coverage_CHILD.json` 与 `weekly_coverage_TEEN.json`），无惧训练进程意外中断或停机重启，历史考核进度零丢失。
- **经典与 Synapse 动态高峰安全闸门：** `TEEN` 阶段智能体仅被允许在平峰及低谷时段向物理硬件施加控制。若 Synapse 未推送动态 `peak_schedule.json`，CARINA 自动退守经典交通工程排程：
  - *周一至周五：* 早高峰（**06:30 至 09:00**）与晚高峰（**17:00 至 19:30**）强制降级为影子模式。
  - *周六与周日：* 全天视为非高峰期（允许受控物理放权）。
- **整周宏观综合考核：** 晋升评估针对全周累积综合表现（$\mu_{\text{week}} \ge \mu_{\text{baseline}} + \delta^*$），杜绝因单日偶然扰动而误杀整体稳健的优秀策略。

### 5.1.3 不可逾越的法定安全不变量
为防止现场操作人员配置疏忽危及城市关键基础设施，系统在底层构建了不可篡改的数学安全铁律：
- **观测时长单向底线：** 管理员可自由延长考察期，但系统绝不允许将考察周期缩短至法定单周底线以下：
  $$t_{\min} = \max(E_{\text{week}}, \text{操作员配置值})$$
- **策略确定性单向顶线（熵下限）：** 管理员可提高确定性标准（要求更低的策略熵），但系统绝不允许放宽熵阈值去接纳混沌高熵策略：
  $$\text{threshold} = \min(E_{\text{calculated}}(t), E_{\text{manual\_operator}})$$

### 5.2 相位内群体进化算法 (Intra-Phase PBT)
为了在多智能体群体进化过程中维护发育阶段的一致性，[`PopulationManager`](../../src/core/population_manager.py) 强制实施严格的生命周期层级隔离：
- **同梯队竞争变异：** 智能体仅在同层级伙伴之间开展权重克隆与超参数变异（$\text{TEEN} \leftrightarrow \text{TEEN}$，$\text{ADULT} \leftrightarrow \text{ADULT}$）。
- **幼年期免疫防护：** 处于 `CHILD` 阶段的智能体被完全屏蔽在变异扰动之外，专注于在纯净状态下被动观测路网物理流动。
- **异构拓扑尺寸安全：** 跨不同车道拓扑进行权重迁移时，内建严格的张量维度动态校验，杜绝形状不匹配崩溃。

### 5.3 动态毕业性能增益裕度计算 ($\delta^*$)
CARINA 摒弃了静态武断的考核标准，智能体从 `TEEN` 晋升至 `ADULT` 所需的超越基准传统控制器的性能增益裕度，完全由历史实测道路流体动力学动态计算求得：

$$\delta^* = K \times \left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right) \times (1 - \text{occupancy}_{\text{child}}) \times 100\%$$

其中各项物理意义为：
- $\left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right)$ 量化了幼年阶段观测到的传统固定配时方案的运行低效度。
- $(1 - \text{occupancy}_{\text{child}})$ 代表道路尚存的物理时空容量裕度。
- $K = 0.25$ 将提升预期与全球主流自适应系统（如 SCATS / SCOOT 的经典提升幅度 $10\%\text{--}15\%$）相标定。
- $\delta^*$ 被严格钳位在 $[3.0\%, 25.0\%]$ 之间，避免在过饱和路网中设定不可企及的目标，或在空旷道路上过早晋升。

### 5.4 物理奖励函数平衡机制 (HCM 道路通行能力物理学)
CARINA 对多目标强化学习奖励函数进行量纲物理对齐，消除排队延误惩罚与通行放行奖励之间的数量级偏差：

$$R(t) = w_{\text{wait}} \times T_{\text{wait}}(t) + w_{\text{flow}} \times F_{\text{discharged}}(t)$$

依据美国公路通行能力手册（HCM）原理，每顺利放行一辆排队车辆，即可为系统挽回相当于整条路段特征行程时间的延误：

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$

[`RewardWeightsCalculator`](../../src/engine/reward_weights_calculator.py) 计算出的物理平衡参数如下：
- $w_{\text{wait}} = -1.0$（排队车辆每秒累积的归一化延误惩罚）。
- $w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$，确保放行车辆的激励权重与累积排队延误在物理尺度上完全匹配。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
