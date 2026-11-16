---
tags: [mfd, analitica, dinamica, densidade, gating, queda-capacidade]
aliases: [Motor MFD, Analítica de Redes, Física de Tráfego, Diagrama Fundamental Macroscópico]
---

# 📈 Diagrama Fundamental Macroscópico (MFD) & Analítica de Rede

Este documento detalha o subsistema de Diagrama Fundamental Macroscópico localizado em [`src/mfd/`](../../src/mfd), o processo dedicado **`MFD_Worker`**, a física do fluxo macroscópico de tráfego, os algoritmos de controle perimetral (*perimeter gating*) e o cache de isolamento de incidentes.

⬅️ [Central de Documentação](carina_moc.md) | 📊 [Justificativas de Engenharia de Tráfego](traffic_engineering_warrants.md) | 🧠 [Notas de Pesquisa & Formulações Neurais](research_notes.md) | 🏛️ [Arquitetura do Sistema](architecture.md)

---

## 1. Teoria do Diagrama Fundamental Macroscópico (MFD)

O **Diagrama Fundamental Macroscópico (MFD)** relaciona o acúmulo total de veículos (densidade $K$) em uma malha urbana com o fluxo médio espacial global ($Q$). Diferentemente dos modelos microscópicos que rastreiam interações veiculares individuais, o MFD fornece uma representação holística da dinâmica de toda a rede viária:

```text
       Q (veic/h)
          ▲                Zona 1: Não-Congestionada (PPO Tático Ativo)
     Qmax │           /\   Zona 2: Queda de Capacidade (Disparo de Gating Perimetral)
          │          /  \  Zona 3: Travamento / Colapso (Intervenção de Emergência)
          │         /    \
          └────────┴──────┴────────► K (veic/km)
                  Kcrit   Kjam
```

- **Zona 1: Região Não-Congestionada ($K < K_{crit}$):** Interseções individuais operam com políticas locais PPO-TCN maximizando a alocação verde adaptativa.
- **Zona 2: Região de Queda de Capacidade (*Capacity Drop*) ($K > K_{crit}$):** O atrito físico e o bloqueio cruzado entre filas degradam drasticamente o escoamento global.
- **Zona 3: Travamento Geral (*Gridlock*) ($K \to K_{jam}$):** Congestionamento arterial generalizado onde os veículos não conseguem desocupar os cruzamentos devido ao transbordamento à frente (*spillback*).

---

## 2. Formulações Matemáticas

A densidade agregada da rede $K_{net}$ e o fluxo médio espacial $Q_{net}$ são calculados como médias ponderadas pelas extensões de todos os $N$ segmentos viários monitorados:

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

Onde:
- $k_i$: Densidade do segmento viário $i$ (veículos por quilômetro).
- $q_i$: Taxa de fluxo do segmento viário $i$ (veículos por hora).
- $L_i$: Comprimento físico do segmento viário $i$ em metros.

---

## 3. Módulos Principais em `src/mfd/`

A suíte analítica do MFD é composta por 35 módulos especializados em [`src/mfd/`](../../src/mfd):

### 3.1 Processo MFD Worker (`mfd_worker.py`)
Executa como um processo de sistema operacional isolado inicializado pelo `ProcessManager` com `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` e `OPENBLAS_NUM_THREADS=1`. Escuta a fila IPC `mfd_trigger`, realiza o parse de malhas SUMO através do cache LRU [`read_sumo_net_cached()`](../../src/utils/sumo_net_cache.py), renderiza curvas offscreen via [`mpl_utils.py`](../../src/rendering/mpl_utils.py), executa a narração SLM sob [`slm_process_lock()`](../../src/slm/slm_lock.py) com `unload()` explícito e retorna os resultados na fila `mfd_results`.

### 3.2 Motor de Comparação & Gerenciador de Linha de Base (`mfd_comparison_engine.py` & `mfd_baseline_manager.py`)
- Compara continuamente o fluxo da IA adaptativa em tempo real com curvas de referência de planos de tempo fixo.
- Computa a economia em Horas de Viagem dos Veículos (VHT) e Quilômetros de Viagem dos Veículos (VKT).

### 3.3 Reconstrutor Histórico (`mfd_history_reconstructor.py`)
Reconstrói diagramas de dispersão fluxo-densidade a partir da tabela PostgreSQL `synapse_fluid_dynamics` em janelas temporais de múltiplos dias.

### 3.4 Calculador de Impacto Urbano (`mfd_impact_calculator.py`)
Quantifica a redução de emissões veiculares municipais ($\text{CO}_2$, $\text{NO}_x$), a economia de combustível e os ganhos econômicos decorrentes da fluidez do tráfego.

---

## 4. Atuação por Controle Perimetral (Gating)

Quando a densidade média da rede excede a capacidade crítica ($K_{net} \ge K_{crit}$):
1. O processo `MFD_Worker` emite um sinal de alerta de *gating* perimetral para o `CentralController`.
2. Interseções nos limites externos da zona crítica estrangulam os tempos de verde de entrada ($T_{green} \leftarrow T_{green} \times \eta$, com $\eta \in [0,6, 0,8]$).
3. Corredores arteriais de saída recebem prioridade máxima de escoamento para evacuar veículos do centro financeiro/comercial congestionado.

---

## 5. Cache de Isolamento de Incidentes (`.carina_incident_filter_cache.json`)

Para evitar que acidentes localizados ou interdições de faixas por obras distorçam a curva macroscópica do MFD, [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py) isola segmentos anômalos e persiste os estados de incidentes ativos em `.carina_incident_filter_cache.json` para recuperação imediata entre reinícios do sistema.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
