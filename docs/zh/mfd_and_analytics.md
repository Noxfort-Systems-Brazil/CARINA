---
tags: [mfd, analytics, dynamics, density, gating, capacity-drop]
aliases: [MFD引擎, 路网宏观分析, 交通流物理学, 宏观基础图]
---

# 📈 宏观基础图 (MFD) 与全路网宏观动力学分析

本文档详尽规范了位于 [`src/mfd/`](../../src/mfd) 的宏观基础图分析子系统、**`MFD_Worker`** 独立微服务进程、宏观交通流物理学原理、边界周界门控控制算法以及异常事件滤波持久化缓存。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 📊 查阅 [交通工程依据](traffic_engineering_warrants.md) | 🧠 查阅 [神经理论推导](research_notes.md)

---

## 1. 宏观基础图 (MFD) 物理理论

**宏观基础图（Macroscopic Fundamental Diagram, MFD）** 建立了城市道路网络内部车辆空间累积总数（路网密度 $K$）与全网空间平均流量（通行能力 $Q$）之间的宏观物理关系。与聚焦微观单车跟驰行为的仿真模型不同，MFD 为全路网尺度的宏观交通运行状态提供了高阶系统级抽象表征。

```text
       Q (辆/小时)
          ▲                区域 1: 自由畅行区 (战术级 PPO 智能体高效自适应配时)
     Qmax │           /\   区域 2: 通行能力骤降区 (触发边界周界门控协同节流)
          │          /  \  区域 3: 网状锁死崩溃区 (触发紧急安全清空强制覆盖)
          │         /    \
          └────────┴──────┴────────► K (辆/公里)
                  Kcrit   Kjam
```

- **区域 1：自由畅行区 ($K < K_{crit}$)：** 各独立交叉口基于本地 PPO-TCN 策略独立优化配时，实现局部放行效率最大化。
- **区域 2：通行能力骤降区 ($K > K_{crit}$)：** 相互交织的排队车流诱发交通物理摩擦，导致全网宏观通行吞吐能力急剧恶化（*Capacity Drop 现象*）。
- **区域 3：网状锁死区 ($K \to K_{jam}$)：** 城市干道网络发生全面溢流回堵，下游溢流导致交叉口无法完成有效车辆清空，路网陷入瘫痪。

---

## 2. 宏观物理数学公式

全路网宏观加权密度 $K_{net}$ 与空间平均流量 $Q_{net}$ 是通过对全网所有 $N$ 条受控道路路段进行空间长度加权平均计算求得：

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

其中：
- $k_i$：路段 $i$ 的局部实测密度（辆/公里）。
- $q_i$：路段 $i$ 的局部实测流量（辆/小时）。
- $L_i$：路段 $i$ 的实际物理道路长度（米）。

---

## 3. `src/mfd/` 核心分析模块

MFD 分析套件包含 [`src/mfd/`](../../src/mfd) 目录下的 35 个专业分析模块：

### 3.1 MFD 独立分析微服务 (`mfd_worker.py`)
作为由 `ProcessManager` 派生的独立操作系统子进程运行。监听 `mfd_trigger` IPC 队列，异步执行宏观非线性曲线拟合回归，并通过 `mfd_results` 队列返回分析结果。

### 3.2 对比评估引擎与基准管理器 (`mfd_comparison_engine.py` 与 `mfd_baseline_manager.py`)
- 持续量化对比当前 AI 自适应控制下的路网通行吞吐量与传统固定配时基准曲线。
- 自动化测算全网车辆总行驶时间（VHT）与总行驶里程（VKT）的节约效益。

### 3.3 历史数据时空重构器 (`mfd_history_reconstructor.py`)
跨越数周或数月的连续观测时间窗口，从 PostgreSQL `synapse_fluid_dynamics` 数据表中重构高密度的流量-密度散点图与拟合包络线。

### 3.4 城市综合效益计算器 (`mfd_impact_calculator.py`)
精准量化因交通拥堵显著缓解而减少的城市汽车尾气排放总量（$\text{CO}_2$、$\text{NO}_x$）、燃油消耗节约量以及城市经济时间生产力增益。

---

## 4. 边界周界门控控制执行 (Perimeter Gating)

当全路网实测密度突破临界容量门限时（$K_{net} \ge K_{crit}$）：
1. `MFD_Worker` 立即向 `CentralController` 派发最高级别的周界门控调控警报。
2. 环绕城市中心拥堵核心区的边缘周界路口自主削减向内汇入方向的绿灯时长（$T_{green} \leftarrow T_{green} \times \eta$，其中削减系数 $\eta \in [0.6, 0.8]$）。
3. 核心区向外疏散的干道走廊则被授予最高放行绿灯配时，加速排空市中心积压滞留车辆。

---

## 5. 异常事件滤波持久化缓存 (`.carina_incident_filter_cache.json`)

为了彻底杜绝因局部突发交通事故或道路施工临时封闭车道而污染宏观 MFD 拟合曲线，[`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py) 自动隔离异常扰动路段，并将活动事件哈希持久化存储于 `.carina_incident_filter_cache.json`，确保系统跨重启生命周期时具备状态连续性。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
