---
tags: [pesquisa, ia, matematica, neural]
aliases: [Notas de Pesquisa, Formulações Matemáticas, PPO-TCN, GOMES]
---

# 🧠 Notas de Pesquisa Neural e Formulações Matemáticas

Este documento detalha o arcabouço matemático, as arquiteturas de redes neurais profundas e as formulações de currículo de maturação que sustentam o **Graph-based Operational Multi-agent Expert System (GOMES)** e o currículo de maturação **DA SILVA** do ecossistema CARINA.

⬅️ [Central de Documentação](README.md) | 🏛️ [Arquitetura do Sistema](architecture.md) | 🛡️ [Segurança e Watchdog](safety_and_watchdog.md) | 🔍 [IA Explicável e SAS](xai_and_sas.md)

---

## 1. PPO-TCN: Redes Convolucionais Temporais sobre LSTMs

Redes Neurais Recorrentes padrão (LSTMs/GRUs) sofrem de desvanecimento de gradiente (*vanishing gradients*) e perda de contexto temporal ao longo de episódios longos durante a retropropagação no tempo (BPTT). O CARINA substitui LSTMs por um backbone de **Rede Convolucional Temporal (TCN)** no Agente Tático PPO.

```text
Tensor de Entrada Histórico: X ∈ ℝ^(B × C × T)
  B: Batch size
  C: Características por instante temporal (ocupação, velocidade, fila, estágio)
  T: Janela de contexto temporal (ex: T = 8 segundos a 10 Hz = 80 quadros)
```

### 1.1 Convoluções Causais Dilatadas

Para assegurar vazamento temporal zero (onde a predição no instante $t$ depende estritamente de instantes $\le t$), a TCN emprega convoluções causais dilatadas 1D:

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

Onde:
- $k$: Tamanho do kernel ($k = 3$)
- $d$: Fator de dilatação ($d = 2^l$ no índice de camada $l \in \{0, 1, 2, 3\}$)
- Tamanho do Campo Receptivo: $RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

A TCN produz um tensor denso de representação temporal $H_{tcn}$, que alimenta as cabeças de Ator (*Actor*) e Crítico (*Critic*) do PPO.

### 1.2 Objetivo Substituto Truncado do PPO (Clipped Surrogate)

A rede de política do PPO é otimizada pelo objetivo substituto truncado (*clipped surrogate objective*) com Estimação de Vantagem Generalizada (GAE):

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

Onde:
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ é a razão de probabilidade.
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ é o estimador de vantagem GAE.
- $\epsilon = 0.2$ é o limite de truncamento (*clipping boundary*) da política.

---

## 2. Autoencoder Preditivo (PAE) e Espaço Latente $Z$

O **Autoencoder Preditivo (PAE)** projeta o risco de transbordamento de filas (*spillback*) a partir de tendências espaço-temporais passadas.

```text
        ┌──────────────┐          ┌───────────────────────┐          ┌──────────────┐
X_hist  │  PAE Encoder │ ───────> │   Gargalo Latente Z   │ ───────> │  PAE Decoder │ ───> X_pred
(t-8s..t)└──────────────┘          │  Z ∈ ℝ^16             │          └──────────────┘      (t+1s..t+30s)
                                   └───────────────────────┘
```

### 2.1 Função de Perda do PAE

O PAE é treinado online e offline utilizando uma função de perda conjunta com Erro Quadrático Médio (MSE) e regularização por divergência de Kullback-Leibler (KL):

$$\mathcal{L}_{PAE} = \underbrace{\| X_{pred} - X_{future} \|_2^2}_{\text{Perda de Reconstrução e Predição}} + \beta \cdot D_{KL}\Big( q_\phi(Z|X) \,\parallel\, \mathcal{N}(0, I) \Big)$$

O vetor latente de 16 dimensões $Z \in \mathbb{R}^{16}$ captura o momento físico das filas e é concatenado ao vetor de entrada do PPO.

---

## 3. Agente Guardião Dueling DQN-TCN

O **Agente Guardião** estima continuamente o **Risco de Spillback** para cada aproximação viária utilizando uma Dueling Deep Q-Network sobre representações de características TCN:

$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

Onde:
- $V(s)$: Valor escalar de linha de base do estado $s$.
- $A(s, a)$: Vantagem de selecionar a ação de fase $a$.

Se $\max_a Q(s, a_{spillback}) > \tau_{risk}$ (onde $\tau_{risk} = 0.8$), o Guardião sobrepõe a fase proposta pelo Agente Tático e força um estágio de limpeza e esvaziamento emergencial.

---

## 4. Camada Estratégica: Redes de Atenção em Grafos (ST-GATv2 Lite)

Para coordenar "Ondas Verdes" sincronizadas em corredores arteriais, o CARINA modela a malha viária como um grafo direcionado $\mathcal{G} = (\mathcal{V}, \mathcal{E})$.

### 4.1 Pesos de Atenção GATv2

Para interseções conectadas $i, j \in \mathcal{V}$, o GATv2 calcula dinamicamente os coeficientes de atenção $\alpha_{ij}$:

$$\alpha_{ij} = \frac{\exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_j] \right) \right)}{\sum_{k \in \mathcal{N}_i} \exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_k] \right) \right)}$$

Onde:
- $h_i, h_j$: Vetores de características do nó $i$ e do nó vizinho $j$.
- $\mathbf{W}$: Matriz de pesos lineares compartilhada.
- $\mathbf{a}$: Vetor de parâmetros de atenção aprendível.

---

## 5. Formulação do Currículo de Maturação DA SILVA

O pipeline **Dynamic Agent Safety Integrated Learning for Validated Autonomy (DA SILVA)** quantifica a maturidade da política através da **Entropia de Shannon da Política**:

$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_{a \in \mathcal{A}} \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

### 5.1 Critérios de Progressão Estagiada e Curva Dinâmica de Entropia

Para garantir que políticas aleatórias nunca sejam promovidas precocemente, a maturação utiliza um teto de entropia limitado pelo espaço de ações $E_{max} = \ln(|\mathcal{A}|)$ (onde $E_{max} = \ln(3) \approx 1,0986$ para 3 ações) ou pela entropia normalizada $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$. O limiar de admissão decai dinamicamente com o tempo configurado pelo usuário ($t$ episódios) via `DynamicEntropyCalculator`:

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

Onde $E_{ideal} = 0,10$, $k = 0,05$ para a transição Criança $\to$ Adolescente e $k = 0,15$ para Adolescente $\to$ Adulto. Os critérios de progressão nominais assintóticos são:

1. **Estágio CRIANÇA (Shadow Mode):** $\mathcal{H} > E_{child}(t)$ (meta nominal assintótica $\mathcal{H} > 0.40$). As ações do agente rodam em modo sombra (apenas telemetria); o controlador legado opera os semáforos físicos. Como $E(t) < \ln(3)$ para todo $t \ge 1$, um agente com escolhas ao acaso ($\mathcal{H} = \ln 3$) é estritamente impedido de progredir. Duração mínima inviolável: 1 semana completa ($E_{\text{semana}}$ episódios calculados via [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py)) para cobertura representativa das 168 faixas horárias reais.
2. **Estágio ADOLESCENTE (Autonomia Restrita):** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$ (faixa nominal $0.15 < \mathcal{H} \le 0.40$). O agente assume o controle físico exclusivamente fora dos horários de pico (definidos pela grade do Synapse ou fallback padrão municipal); durante os picos, opera em modo sombra para segurança viária. Duração mínima inviolável: 1 semana completa ($E_{\text{semana}}$ episódios).
3. **Estágio ADULTO (Autonomia Integral):** $\mathcal{H} \le E_{adult}(t)$ (meta nominal assintótica $\mathcal{H} \le 0.15$, atingida para $t \ge 20$ episódios com $k=0,15$) e Recompensa Média $\mu_{reward} > \mu_{baseline} + \delta^*$. Liberação total da atuação autônoma 24 horas por dia, 7 dias por semana.

### 5.1.1 Dimensionamento Topológico de Passos e Pacing Semanal
Para eliminar números mágicos e calibrar o horizonte de cada episódio com a escala física da malha urbana, o CARINA emprega o [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py):
- **Complexidade Topológica ($C_{\text{topo}}$):** Relação entre conexões físicas reais $E_{\text{real}}$ (com unificação de sentidos bidirecionais de mão dupla e descarte de conexões internas prefixadas com `:`) e semáforos $N$, ponderada pela média de faixas de rolamento $\bar{F}$:
  $$C_{\text{topo}} = \text{clamp}\left( \frac{E_{\text{real}}}{N} \times \left(1.0 + 0.1 \times (\bar{F} - 1.0)\right), \quad 0.8, \quad 1.6 \right)$$
- **Relaxamento Sub-linear:** Previne a explosão de duração em grandes metrópoles escalando com a profundidade do corredor crítico ($\sqrt{N}$) e vão geográfico ($D_{\text{km}}$):
  $$T_{\text{físico}} = 180 + \left( 60 \cdot \sqrt{N} + 30 \cdot D_{\text{km}} \right) \times C_{\text{topo}}$$
- **Passos por Episódio ($S$):** Conversão pessimista a $\Delta t = 250\text{ ms}$ ($4\text{ passos/segundo}$), arredondado para cima na base 10 em múltiplos de 100 e delimitado entre 2,5 minutos ($600\text{ passos}$) e 1 hora ($14.400\text{ passos}$):
  $$S = \text{clamp}\left( \left\lceil \frac{T_{\text{físico}} / 0.25}{100} \right\rceil \times 100, \quad 600, \quad 14400 \right)$$
- **Piso Inviolável de 1 Semana:** Garante a quantidade mínima de episódios para cobrir $604.800\text{ segundos}$ ($7\text{ dias}$):
  $$E_{\text{semana}} = \left\lceil \frac{604800}{S \times 0.25} \right\rceil$$

### 5.1.2 Rastreamento de Cobertura Semanal e Resiliência a Reinicializações
Para garantir que o agente experimente todas as condições viárias reais (dias úteis, madrugadas, picos e finais de semana) antes de qualquer promoção, o [`WeeklyCoverageTracker`](../../src/core/weekly_coverage_tracker.py) opera em conjunto com o [`ActionAuthorizer`](../../src/core/action_authorizer.py):
- **Matriz de 168 Slots de Calendário:** Mapeia exatamente as 168 horas semanais ($7\text{ dias} \times 24\text{ horas}$). Cada passo com timestamp real (`datetime.fromtimestamp(raw_timestamp)`) registra a presença do agente na célula `(dia_da_semana, hora)`.
- **Persistência Atômica:** O progresso da matriz de cobertura é persistido atomicamente em disco (`weekly_coverage_CHILD.json` e `weekly_coverage_TEEN.json`), permitindo pausas, manutenções e reinicializações de processos sem perda de histórico.
- **Gating de Pico Clássico e Synapse:** O estágio `TEEN` atua fisicamente apenas fora do pico. Caso o Synapse não envie a grade dinâmica `peak_schedule.json`, o CARINA adota a engenharia de tráfego clássica:
  - *Segunda a Sexta:* Picos das **06:30 às 09:00** e das **17:00 às 19:30** (Modo Sombra obrigatório).
  - *Finais de Semana:* Fora de pico (Modo Ativo liberado para consolidação).
- **Avaliação Macro / Holística:** A progressão avalia a integral semanal ($\mu_{\text{semana}} \ge \mu_{\text{baseline}} + \delta^*$), impedindo que anomalias isoladas em um único dia (como tempestades severas ou feriados atípicos) reprovem uma política robusta.

### 5.1.3 Invariantes Invioláveis de Segurança
Para proteger a infraestrutura crítica urbana contra configurações imprudentes de operadores, os critérios de maturação implementam invariantes invioláveis:
- **Piso de Tempo Inviolável:** O operador pode aumentar o tempo de observação, mas nunca reduzi-lo abaixo do piso semanal:
  $$t_{\min} = \max(E_{\text{semana}}, \text{configuração\_do\_operador})$$
- **Teto de Certeza (Entropia):** O operador pode exigir maior rigor (menor entropia), mas nunca afrouxar o critério para aceitar políticas caóticas:
  $$\text{limiar\_admissão} = \min(E_{\text{calculado}}(t), E_{\text{manual\_operador}})$$

### 5.2 Algoritmo PBT Intra-Fase
Para preservar a integridade biológica e desenvolvimental das populações de agentes, a evolução genética do [`PopulationManager`](../../src/core/population_manager.py) opera com estrito isolamento por coorte:
- **Agrupamento por Coortes:** Os agentes competem, clonam pesos neurais e sofrem mutação apenas entre seus pares geracionais ($\text{TEEN} \leftrightarrow \text{TEEN}$, $\text{ADULT} \leftrightarrow \text{ADULT}$).
- **Blindagem da Infância:** Agentes na fase `CHILD` ficam isentos de mutações evolutivas e PBT. Seus cérebros observam passivamente a dinâmica física da malha sem perturbação de gradientes ou contaminação cruzada.
- **Segurança de Tensores em Malhas Heterogêneas:** A transferência de pesos entre cruzamentos com diferentes geometrias e números de fases é protegida contra incompatibilidades de dimensões de tensores com validação em tempo de execução.

### 5.3 Margem Dinâmica de Performance para Graduação ($\delta^*$)
Em vez de margens fixas estáticas arbitradas manualmente, a margem de melhoria exigida para promoção de `TEEN` para `ADULT` é calculada continuamente a partir da fluidodinâmica empírica observada durante a infância:

$$\delta^* = K \times \left(1 - \frac{\bar{v}_{\text{infância}}}{v_{\text{limite}}}\right) \times (1 - \text{occupancy}_{\text{infância}}) \times 100\%$$

Onde:
- $\left(1 - \frac{\bar{v}_{\text{infância}}}{v_{\text{limite}}}\right)$ mede a ineficiência herdada dos planos semafóricos legados ou tempos fixos.
- $(1 - \text{occupancy}_{\text{infância}})$ representa a folga física de espaço viário não saturado.
- $K = 0.25$ alinha a meta com a literatura internacional de sistemas adaptativos consolidados (SCATS / SCOOT: $10\%\text{--}15\%$).
- $\delta^*$ é delimitado entre $[3.0\%, 25.0\%]$ para evitar metas matematicamente inatingíveis em malhas saturadas ou graduações precipitadas em vias sem demanda.

### 5.4 Balanceamento Físico de Pesos de Recompensa (HCM)
O CARINA equilibra a função de recompensa multiobjetivo para eliminar o abismo de grandezas entre a penalidade de atraso e o incentivo de vazão:

$$R(t) = w_{\text{wait}} \times T_{\text{wait}}(t) + w_{\text{flow}} \times F_{\text{escoado}}(t)$$

Pela engenharia de tráfego (Highway Capacity Manual - HCM), 1 veículo escoado economiza o tempo livre de travessia característico da via:

$$\tau = \frac{\bar{L}_{\text{vias}}}{\bar{v}_{\text{limite}}}$$

O [`RewardWeightsCalculator`](../../src/engine/reward_weights_calculator.py) calibra automaticamente:
- $w_{\text{wait}} = -1.0$ (penalidade normalizada por segundo de fila).
- $w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$, garantindo que descarregar frentes de veículos tenha a mesma força no gradiente de treinamento que o alívio das filas.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Pesquisa em Inteligência Artificial • CARINA CORE v1.2.0</i>
</div>
