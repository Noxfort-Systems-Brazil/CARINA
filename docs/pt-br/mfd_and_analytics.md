# 📈 Diagrama Fundamental Macroscópico (MFD) e Dinâmica de Redes

Este documento especifica o subsistema de análise macroscópica de tráfego localizado em `src/mfd/`, o processo dedicado `MFD_Worker`, as curvas de fluxo-densidade da malha urbana, os algoritmos de controle perimetral (*perimeter gating*) e o cache de isolamento de incidentes.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](architecture.md) | 🔍 [IA Explicável](xai_and_sas.md)

---

## 1. Teoria do Diagrama Fundamental Macroscópico (MFD)

O MFD relaciona a acumulação total de veículos (densidade de rede $K$) com a capacidade total de escoamento da malha (fluxo médio espacial $Q$):
- **Zona 1 (Não-Congestionada, $K < K_{crit}$):** Operação nominal com maximização de tempos verdes locais via PPO.
- **Zona 2 (Queda de Capacidade / Capacity Drop, $K > K_{crit}$):** Interferência destrutiva entre filas arteriais causando colapso rápido do escoamento.
- **Zona 3 (Gridlock, $K \to K_{jam}$):** Travamento generalizado que exige controle forçado de perímetro.

---

## 2. Controle Perimetral Ativo (Gating)

Quando a densidade agregada ultrapassa o valor crítico ($K_{net} \ge K_{crit}$):
1. O processo `MFD_Worker` emite um sinal de alerta de gating para o `CentralController`.
2. Interseções nos limites externos da zona crítica estrangulam os tempos verdes de entrada ($T_{green} \leftarrow T_{green} \times \eta$, com $\eta \in [0,6, 0,8]$).
3. Corredores de saída recebem prioridade máxima de escoamento para drenar veículos do centro congestionado.
