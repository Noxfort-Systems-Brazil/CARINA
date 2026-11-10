---
tags: [warrants, mutcd, fhwa, traffic-engineering, safety, analysis, sas]
aliases: [交通工程信号依据, 信号设置依据, MUTCD分析, 依据评估器]
---

# 🚦 交通工程信号设置依据与基础设施分析

本文档详尽规范了 CARINA 位于 [`src/analysis/`](../../src/analysis) 的交通工程法定设置依据分析子系统。深入阐述了基于美国 **FHWA MUTCD**（统一交通控制设施手册）以及市政交通工程技术标准的信号控制法定设置依据的数学建模与自动化评估流程。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 📈 查阅 [宏观基础图 (MFD)](mfd_and_analytics.md) | 🔍 查阅 [可解释人工智能与SAS](xai_and_sas.md)

---

## 1. 信号设置依据自动化评估架构

在城市道路规划中新建或调整交通信号灯之前，市政交通工程师必须依法证明目标交叉口满足法定的工程设置依据。**智能分析系统（Smart Analysis System, SAS）** 自动读取持久化于 PostgreSQL 的长期历史微观流体动力学数据，科学研判该交叉口是否确需设置信号灯或优化当前相位配时。

```text
 历史微观交通流数据 (PostgreSQL `synapse_fluid_dynamics`)
                             │
                             ▼
                ┌─────────────────────────┐
                │ InfrastructureAnalyzer  │
                └────────────┬────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────────┐      ┌──────────────────────┐
   │   WarrantEvaluator   │      │     WarrantMath      │
   │   (法定依据评估策略) │      │ (流量与速度数学计算) │
   └──────────┬───────────┘      └──────────────────────┘
              │
              ├──> 依据 1: VolumeWarrant (MUTCD 表 4C-1 交通量)
              ├──> 依据 2: DelayWarrant (不可接受延误 D)
              ├──> 依据 3: QueueWarrant (P95 统计排队长度)
              └──> 依据 4: SaturationWarrant (饱和度 X = v/c)
```

---

## 2. 系统实现的交通工程依据策略 (`src/analysis/warrant_strategies.py`)

CARINA 采用注册于 [`WarrantEvaluator`](../../src/analysis/warrant_evaluator.py) 的**策略模式（Strategy Pattern）**构建其工程分析逻辑：

### 2.1 依据 1：交通量依据 (`VolumeWarrant`)
基于交通流基本方程评估进口道车流交通量：
$$q = k \times (v \times 3.6)$$
- **MUTCD 表 4C-1 门限：** 综合评估进口车道数与限速标准：
  - **主干道 1 车道 / 次干道 1 车道：** 条件 A：$V_{major} \ge 500\text{ 辆/h}$，$V_{minor} \ge 150\text{ 辆/h}$。条件 B：$V_{major} \ge 750\text{ 辆/h}$，$V_{minor} \ge 75\text{ 辆/h}$。
  - **主干道 2+ 车道 / 次干道 2+ 车道：** 条件 A：$V_{major} \ge 600\text{ 辆/h}$，$V_{minor} \ge 200\text{ 辆/h}$。条件 B：$V_{major} \ge 900\text{ 辆/h}$，$V_{minor} \ge 100\text{ 辆/h}$。
- **高速公路 70% 折减系数：** 当主干道法定限速超过 $70\text{ km/h}$（$19.44\text{ m/s}$）时，所有流量判定门限均乘以 $0.70$ 折减（例如：$500 \to 350\text{ 辆/h}$，$150 \to 105\text{ 辆/h}$）。

### 2.2 依据 2：延误依据 (`DelayWarrant`)
量化次要相交进口道相对于自由流旅行时间的实际运行延误：
$$D = \frac{L}{v_{\text{real}}} - \frac{L}{v_{\text{limit}}}$$
- 评估平均延误是否超过不可接受延误门限：
$$D_{avg} > D_{\text{threshold}}$$
- 默认门限：`unacceptable_delay = 90.0 s`。

### 2.3 依据 3：P95 排队长度依据 (`QueueWarrant`)
利用第 95 百分位统计分布审计排队积压，以预防干道交通溢流（Spillback）：
- 根据传感器历史样本计算经验第 95 百分位排队长度 $P95(Q)$。
- 依据满足条件：
$$P95(Q) > Q_{\text{threshold}}$$
- 默认门限：`max_queue_p95 = 15` 辆车。

### 2.4 依据 4：饱和度依据 (`SaturationWarrant`)
评估所有相交进口道的容量比（$v/c$）：
$$X = \frac{q}{N \times f_{\text{ideal}}}$$
其中：
- $q$：区间平均交通量（$\text{辆/h}$）。
- $N$：进口车道数。
- $f_{\text{ideal}}$：单车道理想饱和流率（$1800\text{ 辆/h/车道}$）。
- 当最大车道饱和度超过临界通行能力时满足依据：
$$X_{\max} > X_{\text{critical}}$$
- 默认门限：`saturation_critical = 0.85`（$85\%$ 通行能力）。

---

## 3. 数学工具模块 (`warrant_math.py`)

位于 [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py)：
- **`compute_volume_q(density, speed)`：** 计算空间平均流量 $q = k \times (v \times 3.6)$。
- **`compute_delay(length, v_real, v_limit)`：** 计算相对于法定限速的实际车辆通行延误。
- **`compute_p95(values)`：** 计算经验第 95 百分位排队长度。
- **`compute_saturation_ratio(volume, num_lanes, ideal_flow)`：** 计算车道饱和度（$X = v/c$）。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智慧交通移动工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本开源 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
