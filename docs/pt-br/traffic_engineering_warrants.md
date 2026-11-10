---
tags: [warrants, mutcd, fhwa, engenharia-de-trafego, seguranca, analise, sas]
aliases: [Critérios Semafóricos, Justificativas Semafóricas, Análise MUTCD, Avaliador de Warrants]
---

# 🚦 Critérios Técnicos de Implantação Semafórica (Warrants MUTCD)

Este documento especifica o subsistema de análise de justificativas semafóricas (*engineering warrants*) do CARINA localizado em `src/analysis/`. Ele detalha a formulação matemática e a avaliação automatizada dos critérios regulatórios formais baseados no **FHWA MUTCD** (*Manual on Uniform Traffic Control Devices*) e nas normas técnicas municipais brasileiras (CONTRAN/CET).

⬅️ [Central de Documentação](README.md) | 📈 [Diagrama Fundamental (MFD)](mfd_and_analytics.md) | 🔍 [IA Explicável e SAS](xai_and_sas.md)

---

## 1. Avaliação Automatizada de Justificativas Semafóricas

Antes de implantar ou alterar a programação de um semáforo, engenheiros municipais de tráfego são legalmente obrigados a comprovar que a interseção atende a critérios técnicos rigorosos. O **Smart Analysis System (SAS)** avalia o histórico volumétrico acumulado no PostgreSQL para verificar se a operação semafórica é plenamente justificada ou se requer ajustes temporais.

```text
 Dados Históricos de Tráfego (PostgreSQL `synapse_fluid_dynamics`)
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
  │(Estratégias Warrants)│      │(Matemática de Volume)│
  └──────────┬───────────┘      └──────────────────────┘
             │
             ├──> Warrant 1: VolumeWarrant (Volumes da Tabela MUTCD 4C-1)
             ├──> Warrant 2: DelayWarrant (Atraso Excessivo D)
             ├──> Warrant 3: QueueWarrant (Fila Estatística P95)
             └──> Warrant 4: SaturationWarrant (Grau de Saturação X = v/c)
```

---

## 2. Estratégias de Warrants Implementadas (`src/analysis/warrant_strategies.py`)

O CARINA estrutura sua análise de engenharia viária utilizando o **Padrão Strategy** orquestrado pelo [`WarrantEvaluator`](../../src/analysis/warrant_evaluator.py):

### 2.1 Warrant 1: Volume Veicular (`VolumeWarrant`)
Avalia os volumes de tráfego das aproximações utilizando a equação fundamental do fluxo de tráfego:
$$q = k \times (v \times 3.6)$$
- **Limiares da Tabela MUTCD 4C-1:** Avalia a quantidade de faixas e velocidade limite:
  - **1 Faixa Via Principal / 1 Faixa Via Secundária:** Condição A: $V_{principal} \ge 500\text{ veíc/h}$, $V_{secundaria} \ge 150\text{ veíc/h}$. Condição B: $V_{principal} \ge 750\text{ veíc/h}$, $V_{secundaria} \ge 75\text{ veíc/h}$.
  - **2+ Faixas Via Principal / 2+ Faixas Via Secundária:** Condição A: $V_{principal} \ge 600\text{ veíc/h}$, $V_{secundaria} \ge 200\text{ veíc/h}$. Condição B: $V_{principal} \ge 900\text{ veíc/h}$, $V_{secundaria} \ge 100\text{ veíc/h}$.
- **Fator de Redução de 70% para Alta Velocidade:** Se a velocidade regulamentada da via principal for superior a $70\text{ km/h}$ ($19.44\text{ m/s}$), todos os limiares de volume são multiplicados por $0.70$ (ex.: $500 \to 350\text{ veíc/h}$, $150 \to 105\text{ veíc/h}$).

### 2.2 Warrant 2: Atraso Operacional (`DelayWarrant`)
Quantifica o atraso real experimentado pelo tráfego nas aproximações secundárias em relação ao tempo de viagem em fluxo livre:
$$D = \frac{L}{v_{\text{real}}} - \frac{L}{v_{\text{limit}}}$$
- Avalia se o atraso médio supera o limiar de tolerância:
$$D_{avg} > D_{\text{threshold}}$$
- Limiar padrão: `unacceptable_delay = 90.0 s`.

### 2.3 Warrant 3: Fila Estatística P95 (`QueueWarrant`)
Audita o acúmulo de veículos em fila através do percentil 95 para prevenir retenções arteriais (*spillback*):
- Calcula o comprimento de fila empírico de 95º percentil $P95(Q)$ sobre as amostras coletadas.
- O critério é satisfeito se:
$$P95(Q) > Q_{\text{threshold}}$$
- Limiar padrão: `max_queue_p95 = 15` veículos.

### 2.4 Warrant 4: Grau de Saturação (`SaturationWarrant`)
Avalia a razão volume/capacidade ($v/c$) em todas as faixas de aproximação do cruzamento:
$$X = \frac{q}{N \times f_{\text{ideal}}}$$
Onde:
- $q$: Volume médio espacial ($\text{veíc/h}$).
- $N$: Número de faixas de rolamento.
- $f_{\text{ideal}}$: Fluxo de saturação ideal por faixa ($1800\text{ veíc/h/faixa}$).
- O critério é satisfeito se a razão máxima de saturação exceder a capacidade crítica:
$$X_{\max} > X_{\text{critical}}$$
- Limiar padrão: `saturation_critical = 0.85` ($85\%$ da capacidade).

---

## 3. Utilitários Matemáticos (`warrant_math.py`)

Localizados em `src/analysis/warrant_math.py`:
- **`compute_volume_q(density, speed)`:** Calcula o volume de fluxo $q = k \times (v \times 3.6)$.
- **`compute_delay(length, v_real, v_limit)`:** Calcula o atraso veicular real em função da velocidade limite.
- **`compute_p95(values)`:** Calcula o percentil 95 estatístico da fila.
- **`compute_saturation_ratio(volume, num_lanes, ideal_flow)`:** Calcula o grau de saturação ($X = v/c$).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Tráfego • CARINA CORE v1.2.0</i>
</div>
