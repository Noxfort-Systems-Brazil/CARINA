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
             ├──> Warrant 1: Volume Veicular em Oito Horas
             ├──> Warrant 2: Volume Veicular em Quatro Horas
             ├──> Warrant 3: Volume e Atraso na Hora de Pico
             ├──> Warrant 7: Histórico de Sinistros e Taxa Crítica
             └──> Warrant 8: Coordenação de Rede Viária
```

---

## 2. Critérios MUTCD Implementados em `src/analysis/`

### 2.1 Warrant 1: Volume Veicular em Oito Horas (`warrant_strategies.py`)
Avalia se o volume veicular nas vias que se cruzam atinge os limites mínimos estabelecidos durante quaisquer 8 horas de um dia típico:
- **Condição A (Volume Veicular Mínimo):** Os volumes das vias principal e secundária superam os volumes horários críticos $V_{principal} \ge 500\text{ veíc/h}$ e $V_{secundaria} \ge 150\text{ veíc/h}$.
- **Condição B (Interrupção do Fluxo Contínuo):** O volume na via principal é tão elevado que o tráfego da via secundária sofre atraso excessivo para cruzar ($V_{principal} \ge 750\text{ veíc/h}$ e $V_{secundaria} \ge 75\text{ veíc/h}$).

### 2.2 Warrant 2: Volume Veicular em Quatro Horas
Aplica-se quando o volume nas vias principal e secundária satisfaz as curvas de 4 horas do MUTCD modeladas em `src/analysis/warrant_math.py`.

### 2.3 Warrant 3: Volume e Atraso na Hora de Pico
Avalia se as condições de tráfego durante a hora de maior volume do dia causam atrasos extremos ou riscos severos:
- O atraso total por tempo parado experimentado pelo tráfego em uma aproximação secundária é igual ou superior a 4 veículos-hora (para pista simples).
- O volume na aproximação atinge ou supera 100 veículos por hora.

### 2.4 Warrant 7: Histórico de Sinistros de Trânsito
Avalia se a implantação semafórica reduzirá a ocorrência de colisões e atropelamentos:
- Medidas alternativas de menor impacto não foram suficientes para reduzir os sinistros.
- Registro de cinco ou mais colisões no período de 12 meses do tipo suscetível a redução por sinalização semafórica (ex.: colisões em ângulo reto / transversais).

### 2.5 Warrant 8: Coordenação em Rede Viária
Justifica a semaforização para incentivar a concentração e organização dos fluxos veiculares em corredores arteriais coordenados em rede.

---

## 3. Utilitários Matemáticos (`warrant_math.py`)

Localizados em `src/analysis/warrant_math.py`:
- **Cálculo da Velocidade de 85º Percentil:** Avalia se os limites operacionais exigem fator de redução de 70% nos limiares volumétricos (aplicável quando a via principal opera a $> 70\text{ km/h}$ ou em comunidades rurais isoladas).
- **Razão de Fluxo Crítico:** Calcula o fluxo de saturação por faixa e o grau de saturação ($X = v/c$).
- **Acumulação por Janela Deslizante:** Agrega amostras de séries temporais em intervalos horários estáveis para auditoria forense.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Tráfego • CARINA CORE v1.2.0</i>
</div>
