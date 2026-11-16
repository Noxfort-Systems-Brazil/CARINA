---
tags: [xai, sas, captum, abnt, auditoria-forense, guardian-veto, atribuicao]
aliases: [IA Explicável, Analítica SAS, Pipeline XAI, Auditoria Forense]
---

# 🔍 IA Explicável (XAI), Auditoria Forense & Analítica SAS

Este documento especifica o pipeline de explicabilidade forense do CARINA localizado em [`src/xai/`](../../src/xai) e [`src/sas/`](../../src/sas). Ele detalha o uso do **Google Captum Integrated Gradients**, as 5 equações neurais formais, as tabelas de auditoria de vetos do Guardian Agent e a geração de laudos periciais em estrita conformidade com a norma **ABNT NBR 14724**.

⬅️ [Central de Documentação](carina_moc.md) | 📄 [Blocos de Relatório & Word](report_blocks_and_templates.md) | 🤖 [Modelos de Linguagem Locais (SLM)](slm_and_local_llm.md) | 🏛️ [Arquitetura](architecture.md)

---

## 1. Arquitetura de Explicabilidade Forense (`src/xai/`)

Na gestão pública municipal e na engenharia de tráfego, decisões automatizadas tomadas como "caixas-pretas" são juridicamente inaceitáveis perante o Ministério Público, Tribunais de Contas e auditores periciais. O CARINA provê **100% de transparência matemática determinística**:

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │   Rede Neural Profunda  │ ───────> │ Captum Integrated         │ ───────> │  Laudo ABNT NBR 14724  │ ───> Forensic xai.docx
 │ (TCN + ST-GATv2 + D3QN) │          │ Gradients (0% a 100%)     │          │  5 Equações Formais +  │      (Laudo Pericial Municipal)
 └─────────────────────────┘          └───────────────────────────┘          │  Tabela de Vetos       │
                                                                             └────────────────────────┘
```

O pipeline de XAI emprega uma arquitetura modular de construção de laudos multiagente:
- [`src/xai/xai_worker.py`](../../src/xai/xai_worker.py) e [`report_pipeline.py`](../../src/xai/report_pipeline.py): Executam a atribuição do Captum por agente uma única vez e reutilizam o cache resultante `captum_result` (`precomputed_analyses`) na geração consolidada do laudo multiagente, restringindo a síntese textual pesada do SLM (`run_slm`) estritamente ao agente-alvo primário sob `slm_process_lock()` e acessando o banco via `DatabaseManager.get_instance(..., enable_step_worker=False)`.
- [`src/xai/multi_agent_report_builder.py`](../../src/xai/multi_agent_report_builder.py): Orquestra a geração de relatórios periciais para todos os cruzamentos da malha.
- [`src/xai/captum_attribution_engine.py`](../../src/xai/captum_attribution_engine.py): Calcula atribuições de gradiente ao longo do caminho de interpolação entre a linha de base e a entrada atual com gradientes dos parâmetros do modelo encapsulado congelados (`requires_grad_(False)`).
- [`src/xai/network_attribution_aggregator.py`](../../src/xai/network_attribution_aggregator.py): Consolida a importância das variáveis físicas ao longo de corredores arteriais inteiros.
- [`src/xai/report_block_registry.py`](../../src/xai/report_block_registry.py): Despacha seções do relatório para renderizadores especializados (com renderização offscreen de gráficos via `mpl_utils.py`).
- [`src/sas/sas_helpers.py`](../../src/sas/sas_helpers.py) e [`sas_historical_data_processor.py`](../../src/sas/sas_historical_data_processor.py): Calculam 100 quantis em uma única passagem via `TrafficMetricsCalculator.compute_percentiles` e evitam expansão redundante de amostras sintéticas (`SyntheticSampleGenerator`).

---

## 2. As 5 Equações Neurais Formais (Seção 2 do Laudo)

Para atender aos rigorosos critérios de auditoria judicial e administrativa, o laudo pericial gerado pelo CARINA detalha as 5 equações matemáticas que governam cada camada neural:

### 2.1 Convolução Causal Dilatada (LocalAgent TCN)
$$\mathbf{y}(t) = (x *_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

### 2.2 Atenção em Grafo Espaço-Temporal (ST-GATv2 Lite)
$$\alpha_{ij}(t) = \frac{\exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\left(\mathbf{a}^T \text{LeakyReLU}\left(\mathbf{W} [\mathbf{h}_i \parallel \mathbf{h}_k]\right)\right)}$$

### 2.3 Formulação do Autoencoder Preditivo (PAE)
$$\mathcal{L}_{\text{PAE}}(\phi, \theta) = \frac{1}{N} \sum_{k=1}^N \| x_k(t + \Delta t) - g_\theta(f_\phi(x_k(t))) \|^2$$

### 2.4 Valor Q Dueling de Segurança do Guardian (D3QN Veto)
$$Q(s, a) = V(s) + \left( A(s, a) - \frac{1}{|\mathcal{A}|} \sum_{a'} A(s, a') \right)$$

### 2.5 Gradientes Integrados do Captum (Axioma de Completude)
$$\text{IntegratedGradients}_i(x) = (x_i - x'_i) \times \int_0^1 \frac{\partial F(x' + \alpha(x - x'))}{\partial x_i} d\alpha$$

$$\sum_{i=1}^n \text{IntegratedGradients}_i(x) = F(x) - F(x')$$

---

## 3. Tabela Pericial de Auditoria de Vetos do Guardian Agent

O gerador de laudos consulta a tabela PostgreSQL `step_decisions` para montar a **Tabela Pericial de Auditoria de Vetos do Guardian**:

| ID da Interseção | Decisões Avaliadas | Ações Aprovadas | Vetos de Segurança | Taxa de Conformidade (%) | Causa Raiz Primária do Veto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cruzamento ID 1193472566** | 1.420 | 1.396 | 24 | **98,3%** | Proteção de Tempo Mínimo de Verde (7s) |
| **Cruzamento ID 2281940123** | 1.420 | 1.418 | 2 | **99,8%** | Imposição de Entreverde Amarelo (3s) |

Para detalhes sobre a formatação de documentos Word e renderização de fórmulas em OMML, consulte [Blocos de Relatório & Modelos Word](report_blocks_and_templates.md).
Para detalhes sobre a síntese em linguagem natural offline, consulte [Modelos Locais de Linguagem (SLM)](slm_and_local_llm.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
