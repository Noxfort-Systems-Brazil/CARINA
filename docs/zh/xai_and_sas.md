---
tags: [xai, sas, captum, abnt, forensic-audit, guardian-veto, attribution]
aliases: [可解释人工智能, SAS分析, XAI生产管线, 司法级审计]
---

# 🔍 可解释人工智能 (XAI)、司法级取证审计与 SAS 分析

本文档详尽规范了 CARINA 位于 [`src/xai/`](../../src/xai) 与 [`src/sas/`](../../src/sas) 的司法取证级可解释性生产管线。深入剖析了 **Google Captum 积分梯度归因算法（Integrated Gradients）**、5 个核心神经网络形式化数学公式、Guardian 安全否决审计表格以及符合 ABNT NBR 14724 标准的工程报表自动化生成体系。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 📄 查阅 [报告生成引擎](report_blocks_and_templates.md) | 🤖 查阅 [端侧大语言模型 (SLM)](slm_and_local_llm.md)

---

## 1. 司法取证级可解释性生产架构 (`src/xai/`)

在现代城市市政交通管理与公共决策中，“黑盒”人工智能决策是公共检察机关、审计法院（Tribunal de Contas）以及注册交通工程师所无法采信和合法准入的。CARINA 通过以下工程闭环提供 **100% 确定性的数学可解释性**：

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │ 深度神经网络复合架构    │ ───────> │ Google Captum 积分梯度    │ ───────> │ ABNT NBR 14724 审计报表│ ───> 司法审计 xai.docx
 │ (TCN + ST-GATv2 + D3QN) │          │ 空间特征归因 (0% 至 100%) │          │ 5大形式化数学公式 +    │      (市政官方审计报告)
 └─────────────────────────┘          └───────────────────────────┘          │ Guardian 否决记录表格  │
                                                                             └────────────────────────┘
```

XAI 生产管线采用基于微服务理念的模块化构建架构：
- [`src/xai/multi_agent_report_builder.py`](../../src/xai/multi_agent_report_builder.py)：主调度器，统筹全城各受控交叉口的工程审计报表生成。
- [`src/xai/captum_attribution_engine.py`](../../src/xai/captum_attribution_engine.py)：计算从基线全零状态到实测输入状态插值路径上的路径积分梯度。
- [`src/xai/network_attribution_aggregator.py`](../../src/xai/network_attribution_aggregator.py)：聚合整条主干道走廊上的特征敏感度重要性评分。
- [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py)：将文档各章节动态派发至专用的矢量与排版渲染器。

---

## 2. 核心神经网络 5 大形式化数学公式（报告第 2 节）

为满足市政工程司法审计的严苛标准，CARINA 的技术审计报告在第 2 节中规范化包含了支配各神经网络层的 5 个 LaTeX 数学公式：

### 2.1 因果空洞卷积时序特征提取 (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 时空图注意力相邻路口协同 (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 预测自编码器潜在物理流形 (PAE)
$$\mathcal{L}_{\text{PAE}}(\phi, \theta) = \frac{1}{N} \sum_{k=1}^N \| x_k(t + \Delta t) - g_\theta(f_\phi(x_k(t))) \|^2$$

### 2.4 Guardian 安全防火墙竞争优势 Q 价值 (D3QN Veto)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Captum 积分梯度归因与完备性公理 (Integrated Gradients)
$$\text{IntegratedGradients}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{IntegratedGradients}_i(x) = F(x) - F(x')$$

---

## 3. Guardian 守卫智能体安全否决官方审计表格

报告通过查询 PostgreSQL 数据库中的 `step_decisions` 数据表，自动生成法医级 **Guardian 智能体安全否决官方审计统计表**：

| 交叉口节点标识 | 决策提议总次数 | 批准执行动作 | 安全否决拦截 | 安全合规率 (%) | 否决触发核心物理诱因 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **交叉口 ID 1193472566** | 1,420 | 1,396 | 24 | **98.3%** | 最短绿灯保护限制 (7s) |
| **交叉口 ID 2281940123** | 1,420 | 1,418 | 2 | **99.8%** | 黄灯安全过渡间隔保障 (3s) |

有关 Word 文档自动化生成与原生 OMML 数学公式排版，请参阅 [报告模块引擎与Word生成](report_blocks_and_templates.md)。
关于完全离线的端侧大语言模型自然语言生成，请参阅 [端侧轻量大模型 (SLM)](slm_and_local_llm.md)。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
