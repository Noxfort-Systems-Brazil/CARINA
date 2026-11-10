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

### 5.1 Critérios de Progressão Estagiada

1. **Estágio CRIANÇA (Shadow Mode):** $\mathcal{H} > 0.40$. As ações do agente rodam em modo sombra (apenas telemetria); o controlador legado opera os semáforos físicos.
2. **Estágio ADOLESCENTE (Autonomia Restrita):** $0.15 < \mathcal{H} \le 0.40$. O agente assume o controle físico apenas em horários de baixo risco (01:00 às 04:00 da madrugada).
3. **Estágio ADULTO (Autonomia Integral):** $\mathcal{H} \le 0.15$ e Recompensa Média $\mu_{reward} > \mu_{baseline} + 2\sigma$. Liberação total da atuação autônoma 24 horas por dia, 7 dias por semana.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Pesquisa em Inteligência Artificial • CARINA CORE v1.2.0</i>
</div>
