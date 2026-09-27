# 🔍 IA Explicável (XAI), Auditoria Forense Municipal e SAS

Este documento especifica o pipeline de explicabilidade forense do CARINA localizado em `src/xai/` e `src/sas/`. Ele detalha o uso do **Google Captum Integrated Gradients**, as 5 equações neurais formais, as tabelas de auditoria de vetos do Guardian e a geração de laudos periciais em Microsoft Word (`.docx`) em estrita conformidade com a norma brasileira **ABNT NBR 14724**.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](architecture.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md)

---

## 1. Arquitetura de Explicabilidade Forense

Na administração pública e na engenharia de tráfego, decisões de IA tomadas como "caixas-pretas" são inaceitáveis perante o Ministério Público e os Tribunais de Contas. O CARINA provê **100% de transparência matemática**:

```text
 ┌─────────────────────────┐          ┌───────────────────────────┐          ┌────────────────────────┐
 │   Rede Neural Profunda  │ ───────> │ Captum Integrated         │ ───────> │ Laudo Pericial ABNT    │ ───> xai.docx
 │ (TCN + ST-GATv2 + D3QN) │          │ Gradients (0% a 100%)     │          │ 5 Equações Formais +   │      (Laudo Oficial)
 └─────────────────────────┘          └───────────────────────────┘          │ Tabela de Vetos        │
                                                                             └────────────────────────┘
```

---

## 2. As 5 Equações Neurais Formais do Laudo Pericial

Para atender às exigências de auditabilidade forense, o relatório inclui as 5 equações formais renderizadas em Office Math Markup Language (OMML):
1. **Convolução Causal Dilatada (LocalAgent TCN):** Extração de padrões temporais sem vazamento futuro.
2. **Atenção em Grafo Espaço-Temporal (ST-GATv2 Lite):** Ponderação de onda verde arterial entre nós adjacentes.
3. **Fusão de Atenção Cruzada Multimodal (Transformer):** Integração das perspectivas tática e estratégica.
4. **Valor Q Dueling de Segurança (Guardian D3QN):** Estimativa do risco de enfileiramento bloqueante (*spillback*).
5. **Gradientes Integrados do Captum (Axioma de Completude):** Atribuição percentual de causalidade para cada variável observada (filas, ocupação, velocidades).

---

## 3. Tabela Pericial de Auditoria de Vetos

O relatório consulta a tabela PostgreSQL `step_decisions` para consolidar o histórico de conformidade por cruzamento:
- Total de decisões avaliadas.
- Ações aprovadas pela barreira de segurança.
- Vetos de segurança disparados (tempo de verde mínimo, entreverdes de amarelo, risco de spillback).
- Taxa de conformidade do sistema (tipicamente $> 98\%$).
