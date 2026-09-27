---
tags: [xai, sas, captum, abnt, forensic-audit, guardian-veto, attribution]
aliases: [Explainable AI, SAS Analytics, XAI Pipeline, Forensic Auditing]
---

# 🔍 Explainable AI (XAI), Forensic Auditing & SAS Analytics

This document specifies CARINA's forensic explainability pipeline located in [`src/xai/`](../../src/xai) and [`src/sas/`](../../src/sas). It details **Google Captum Integrated Gradients**, the 5 formal neural equations, Guardian Agent safety veto audit tables, and ABNT NBR 14724 report generation.

⬅️ Back to [Main Documentation Hub](../CARINA_MOC.md) | 📄 See [Report Blocks & Word](../REPORT_BLOCKS_AND_TEMPLATES.md) | 🤖 See [Small Language Models](../SLM_AND_LOCAL_LLM.md)

---

## 1. Forensic Explainability Architecture (`src/xai/`)

In municipal traffic management, black-box AI decisions are legally unacceptable to public prosecutors, audit courts (Tribunal de Contas), and certified traffic engineers. CARINA provides **100% deterministic mathematical explainability** through:

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │  Deep Neural Network    │ ───────> │ Captum Integrated         │ ───────> │  ABNT NBR 14724 Report │ ───> Forensic xai.docx
 │  (TCN + ST-GATv2 + D3QN)│          │ Gradients (0% to 100%)    │          │  5 Formal Equations +  │      (Municipal Audit Report)
 └─────────────────────────┘          └───────────────────────────┘          │  Guardian Veto Table   │
                                                                             └────────────────────────┘
```

The XAI pipeline uses a modular multi-agent builder architecture:
- [`src/xai/multi_agent_report_builder.py`](../../src/xai/multi_agent_report_builder.py): Coordinates the generation of municipal reports across all intersections.
- [`src/xai/captum_attribution_engine.py`](../../src/xai/captum_attribution_engine.py): Computes gradient attributions along the interpolation path from baseline to current input.
- [`src/xai/network_attribution_aggregator.py`](../../src/xai/network_attribution_aggregator.py): Aggregates feature importance across arterial avenues.
- [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py): Dispatches report sections to specialized renderers.

---

## 2. The 5 Formal Neural Equations (Section 2 of Report)

To comply with administrative auditability standards, CARINA's report includes 5 formal LaTeX equations governing every neural layer:

### 2.1 Causal Dilated Convolution (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 Spatiotemporal Graph Attention (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 Multimodal Cross-Attention Fusion (Transformer)
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k} \cdot \tau}\right) V$$

### 2.4 Guardian Safety Dueling Q-Value (D3QN Veto)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Captum Integrated Gradients (Completeness Axiom)
$$\text{IntegratedGradients}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{IntegratedGradients}_i(x) = F(x) - F(x')$$

---

## 3. Guardian Agent Veto Audit Table

The report queries PostgreSQL `step_decisions` to generate the official **Guardian Agent Safety Veto Audit Table**:

| Intersection ID | Evaluated Decisions | Approved Actions | Safety Vetoes | Compliance Rate (%) | Primary Root Cause of Veto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Junction ID 1193472566** | 1,420 | 1,396 | 24 | **98.3%** | Minimum Green Time Protection (7s) |
| **Junction ID 2281940123** | 1,420 | 1,418 | 2 | **99.8%** | Yellow Clearance Enforcement (3s) |

For document formatting and OMML math rendering details, see [Report Blocks & Word](../REPORT_BLOCKS_AND_TEMPLATES.md).
For offline natural language justification synthesis, see [Small Language Models (SLM)](../SLM_AND_LOCAL_LLM.md).
