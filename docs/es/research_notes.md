---
tags: [investigacion, ia, matematicas, neuronal]
aliases: [Investigación Neuronal, Formulaciones Matemáticas, PPO-TCN, GOMES]
---

# 🧠 Investigación Neuronal y Formulaciones Matemáticas

Este documento detalla el marco matemático, las arquitecturas de redes neuronales y las formulaciones curriculares subyacentes al **Graph-based Operational Multi-agent Expert System (GOMES)** de CARINA y al currículo de maduración **DA SILVA**.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🏛️ Ver [Arquitectura de Multiprocesamiento](architecture.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🔍 Ver [IA Explicable y SAS](xai_and_sas.md)

---

## 1. PPO-TCN: Redes Convolucionales Temporales sobre LSTMs

Las Redes Neuronales Recurrentes estándar (LSTM/GRU) sufren de desvanecimiento de gradiente y pérdida de contexto temporal durante la retropropagación en el tiempo en episodios prolongados (BPTT). CARINA reemplaza las LSTM con una red troncal de **Red Convolucional Temporal (TCN)** en el Agente Táctico PPO.

```text
Tensor de Entrada Histórico: X ∈ ℝ^(B × C × T)
  B: Tamaño del lote (Batch size)
  C: Características por paso temporal (ocupación, velocidad, cola, fase)
  T: Ventana de contexto temporal (ej., T = 8 segundos a 10Hz = 80 tramas)
```

### 1.1 Convoluciones Causales Dilatadas

Para garantizar cero filtración temporal (la predicción en el instante $t$ depende exclusivamente de marcas temporales $\le t$), la TCN utiliza convoluciones causales dilatadas en 1D:

$$y(t) = (x \star_d f)(t) = \sum_{i=0}^{k-1} f(i) \cdot x(t - d \cdot i)$$

Donde:
- $k$: Tamaño del kernel ($k = 3$)
- $d$: Factor de dilatación ($d = 2^l$ en el índice de capa $l \in \{0, 1, 2, 3\}$)
- Tamaño del Campo Receptivo: $RF = 1 + \sum_{l=0}^{L-1} (k - 1) \cdot d_l$

La TCN genera un tensor denso de representación temporal $H_{tcn}$, que alimenta a los cabezales del Actor y el Crítico de PPO.

### 1.2 Objetivo Subrogado Recortado de PPO

La red de política de PPO se optimiza mediante la función objetivo subrogada recortada con Estimación de Ventaja Generalizada (GAE):

$$L^{CLIP}(\theta) = \hat{\mathbb{E}}_t \left[ \min \left( r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

Donde:
- $r_t(\theta) = \frac{\pi_\theta(a_t | s_t)}{\pi_{\theta_{old}}(a_t | s_t)}$ es el ratio de probabilidades.
- $\hat{A}_t = \sum_{l=0}^{\infty} (\gamma \lambda)^l \delta_{t+l}^V$ es el estimador de ventaja GAE.
- $\epsilon = 0.2$ es el límite de recorte de la política.

---

## 2. Autoencoder Predictivo (PAE) y Espacio Latente $Z$

El **Autoencoder Predictivo (PAE)** predice desbordamientos futuros de colas de tráfico basándose en tendencias espacio-temporales previas.

```text
         ┌──────────────┐          ┌───────────────────────┐          ┌──────────────┐
X_hist   │ Encoder PAE  │ ───────> │ Cuello de Botella Z   │ ───────> │ Decodific.PAE│ ───> X_pred
(t-8s..t)└──────────────┘          │ Z ∈ ℝ^16              │          └──────────────┘      (t+1s..t+30s)
                                   └───────────────────────┘
```

### 2.1 Función de Pérdida del PAE

El PAE se entrena tanto offline como online utilizando una regularización conjunta de Error Cuadrático Medio (MSE) y divergencia de Kullback-Leibler (KL):

$$\mathcal{L}_{PAE} = \underbrace{\| X_{pred} - X_{future} \|_2^2}_{\text{Pérdida de Reconstrucción y Predicción}} + \beta \cdot D_{KL}\Big( q_\phi(Z|X) \,\parallel\, \mathcal{N}(0, I) \Big)$$

El vector latente de 16 dimensiones $Z \in \mathbb{R}^{16}$ captura el momento físico de las colas de tráfico y se concatena al vector de entrada del PPO.

---

## 3. Agente Guardian Dueling DQN-TCN

El **Agente Guardian** estima continuamente el **Riesgo de Desbordamiento (Spillback Risk)** para cada carril de la intersección utilizando una red Dueling Deep Q-Network sobre representaciones de características TCN:

$$Q(s, a; \theta, \alpha, \beta) = V(s; \theta, \beta) + \left( A(s, a; \theta, \alpha) - \frac{1}{|\mathcal{A}|} \sum_{a' \in \mathcal{A}} A(s, a'; \theta, \alpha) \right)$$

Donde:
- $V(s)$: Valor base escalar del estado $s$.
- $A(s, a)$: Ventaja de ejecutar la acción de fase $a$.

Si $\max_a Q(s, a_{spillback}) > \tau_{risk}$ (donde $\tau_{risk} = 0.8$), el Guardian anula la fase propuesta por el Agente Táctico y fuerza una fase de desahogo de emergencia.

---

## 4. Capa Estratégica: Redes de Atención en Grafos (GATv2 Lite)

Para coordinar "Ondas Verdes" multi-intersección a lo largo de avenidas arteriales, CARINA modela la red vial como un grafo dirigido $\mathcal{G} = (\mathcal{V}, \mathcal{E})$.

### 4.1 Pesos de Atención GATv2

Para intersecciones conectadas $i, j \in \mathcal{V}$, GATv2 calcula coeficientes dinámicos de atención $\alpha_{ij}$:

$$\alpha_{ij} = \frac{\exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_j] \right) \right)}{\sum_{k \in \mathcal{N}_i} \exp\left( \mathbf{a}^T \text{LeakyReLU}\left( \mathbf{W} [h_i \,\|\, h_k] \right) \right)}$$

Donde:
- $h_i, h_j$: Representaciones de características del nodo $i$ y del nodo vecino $j$.
- $\mathbf{W}$: Matriz de pesos compartida.
- $\mathbf{a}$: Vector de atención aprendible.

---

## 5. Formulación del Currículo de Maduración DA SILVA

La canalización **DA SILVA** (Dynamic Agent Safety Integrated Learning for Validated Autonomy) evalúa la madurez de la política utilizando la **Entropía de Shannon de la Política**:

$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_{a \in \mathcal{A}} \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

### 5.1 Criterios de Progresión y Curva de Decaimiento Dinámico de Entropía

Para garantizar que las políticas aleatorias nunca sean promovidas de forma prematura, la madurez de la política utiliza un techo de entropía acotado por las acciones $E_{max} = \ln(|\mathcal{A}|)$ (donde $E_{max} = \ln(3) \approx 1.0986$ para 3 acciones) o entropía normalizada $\mathcal{H}_{norm} = \mathcal{H} / \ln(|\mathcal{A}|) \in [0, 1]$. El umbral de admisión decae dinámicamente según la duración configurada por el usuario ($t$ episodios) mediante `DynamicEntropyCalculator`:

$$E(t) = E_{ideal} + (E_{max} - E_{ideal}) \cdot e^{-k \cdot t}$$

Donde $E_{ideal} = 0.10$, $k = 0.05$ para la transición Child $\to$ Teen, y $k = 0.15$ para la transición Teen $\to$ Adult. Las metas nominales de progresión asintótica son:

1. **Etapa CHILD (Modo Shadow):** $\mathcal{H} > E_{child}(t)$ (meta asintótica nominal $\mathcal{H} > 0.40$). Las acciones operan estrictamente en modo sombra (solo telemetría pasiva); el controlador base opera el hardware. Dado que $E(t) < \ln(3)$ para todo $t \ge 1$, una política puramente aleatoria ($\mathcal{H} = \ln 3$) tiene estrictamente prohibido graduarse. Duración mínima inviolable: 1 semana completa ($E_{\text{semana}}$ episodios calculados mediante [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py)) para cubrir las 168 franjas horarias reales.
2. **Etapa TEEN (Autonomía Restringida):** $E_{adult}(t) < \mathcal{H} \le E_{child}(t)$ (rango nominal $0.15 < \mathcal{H} \le 0.40$). El agente opera el hardware físico exclusivamente fuera de los horarios punta (definidos por Synapse o el estándar urbano clásico); durante las horas punta, regresa a modo sombra por seguridad vial. Duración mínima inviolable: 1 semana completa ($E_{\text{semana}}$ episodios).
3. **Etapa ADULT (Autonomía Completa):** $\mathcal{H} \le E_{adult}(t)$ (meta asintótica nominal $\mathcal{H} \le 0.15$, alcanzada en $t \ge 20$ episodios con $k=0.15$) y Recompensa Media $\mu_{reward} > \mu_{baseline} + \delta^*$. Se otorga actuación autónoma total 24/7 en todas las condiciones de tráfico.

### 5.1.1 Dimensionamiento Topológico de Pasos y Pacing Semanal
Para eliminar números mágicos y calibrar el horizonte de cada episodio con la escala física de la red urbana, CARINA emplea el [`EpisodeStepCalculator`](../../src/utils/episode_step_calculator.py):
- **Complejidad Topológica ($C_{\text{topo}}$):** Relación entre conexiones físicas reales $E_{\text{real}}$ (unificando sentidos bidireccionales y descartando conectores internos con `:`) y semáforos $N$, ponderada por el promedio de carriles $\bar{F}$:
  $$C_{\text{topo}} = \text{clamp}\left( \frac{E_{\text{real}}}{N} \times \left(1.0 + 0.1 \times (\bar{F} - 1.0)\right), \quad 0.8, \quad 1.6 \right)$$
- **Relajación Sub-lineal:** Previene la explosión de duración en grandes urbes escalando con la profundidad del corredor crítico ($\sqrt{N}$) y el diámetro geográfico ($D_{\text{km}}$):
  $$T_{\text{físico}} = 180 + \left( 60 \cdot \sqrt{N} + 30 \cdot D_{\text{km}} \right) \times C_{\text{topo}}$$
- **Pasos por Episodio ($S$):** Conversión pesimista a $\Delta t = 250\text{ ms}$ ($4\text{ pasos/segundo}$), redondeado al alza en base 10 en múltiplos de 100 y delimitado entre 2,5 minutos ($600\text{ pasos}$) y 1 hora ($14.400\text{ pasos}$):
  $$S = \text{clamp}\left( \left\lceil \frac{T_{\text{físico}} / 0.25}{100} \right\rceil \times 100, \quad 600, \quad 14400 \right)$$
- **Piso Inviolable de 1 Semana ($E_{\text{semana}}$):** Cantidad mínima de episodios para observar exactamente 7 días completos ($604.800\text{ segundos}$):
  $$E_{\text{semana}} = \left\lceil \frac{604800}{S \times 0.25} \right\rceil$$

### 5.1.2 Rastreo de Cobertura Semanal y Resiliencia ante Reinicios
Para verificar que la evaluación de la política abarque todas las condiciones viarias reales (días laborables, madrugadas, horas punta y fines de semana) antes de la promoción, el [`WeeklyCoverageTracker`](../../src/core/weekly_coverage_tracker.py) opera junto al [`ActionAuthorizer`](../../src/core/action_authorizer.py):
- **Matriz de 168 Slots de Calendario:** Mapea las 168 horas semanales ($7\text{ días} \times 24\text{ horas}$). Cada trama con timestamp real (`datetime.fromtimestamp(raw_timestamp)`) registra su presencia en la celda `(dia_semana, hora)`.
- **Persistencia Atómica:** El estado de cobertura se guarda atómicamente en disco (`weekly_coverage_CHILD.json` y `weekly_coverage_TEEN.json`), tolerando pausas y reinicios sin perder progreso.
- **Control de Picos Clásico y Synapse:** La fase `TEEN` solo actúa físicamente fuera de las horas punta. Si Synapse no envía el archivo dinámico `peak_schedule.json`, CARINA adopta la ingeniería de tráfico clásica:
  - *Lunes a Viernes:* Horas punta matutina (**06:30 a 09:00**) y vespertina (**17:00 a 19:30**) en modo sombra.
  - *Fines de Semana:* Fuera de pico (modo activo permitido).
- **Evaluación Macro Holística:** La promoción evalúa el rendimiento acumulado semanal ($\mu_{\text{semana}} \ge \mu_{\text{baseline}} + \delta^*$), impidiendo que anomalías aisladas en un solo día descarten una política segura.

### 5.1.3 Invariantes Inviolables de Seguridad
Para proteger la infraestructura crítica urbana frente a configuraciones imprudentes, se imponen invariantes matemáticas estrictas:
- **Piso de Tiempo Inviolável:** Los operadores pueden configurar mayor observación, pero nunca reducirla por debajo del piso semanal:
  $$t_{\min} = \max(E_{\text{semana}}, \text{configuracion\_operador})$$
- **Techo de Certeza (Piso de Entropía):** Los operadores pueden exigir mayor certidumbre (menor entropía), pero nunca relajar el criterio para aceptar políticas caóticas:
  $$\text{umbral} = \min(E_{\text{calculado}}(t), E_{\text{manual\_operador}})$$

### 5.2 Entrenamiento Basado en Población (PBT) Intra-Fase
Para asegurar la integridad biológica y evolutiva entre las cohortes de agentes, la explotación y exploración evolutiva en [`PopulationManager`](../../src/core/population_manager.py) operan bajo estricto aislamiento intra-fase:
- **Agrupamiento por Cohorte:** Los agentes compiten, clonan pesos y mutan hiperparámetros estrictamente dentro de su misma etapa de ciclo de vida ($\text{TEEN} \leftrightarrow \text{TEEN}$, $\text{ADULT} \leftrightarrow \text{ADULT}$).
- **Protección de la Infancia:** Los agentes en la etapa `CHILD` están exentos de mutaciones evolutivas. Sus pesos neuronales permanecen inalterados mientras observan la dinámica de la red física.
- **Seguridad ante Heterogeneidad Topológica:** La transferencia de pesos entre topologías de intersección disímiles está protegida contra discordancias de dimensiones tensoriales mediante validación de formas en tiempo de ejecución.

### 5.3 Margen de Rendimiento Dinámico de Graduación ($\delta^*$)
En lugar de umbrales estáticos arbitrarios, el margen de graduación requerido para que un agente avance de `TEEN` a `ADULT` se calcula de forma continua a partir de la dinámica empírica de fluidos del tráfico:

$$\delta^* = K \times \left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right) \times (1 - \text{occupancy}_{\text{child}}) \times 100\%$$

Donde:
- $\left(1 - \frac{\bar{v}_{\text{child}}}{v_{\text{limit}}}\right)$ cuantifica la ineficiencia operativa de los planes de señales heredados observada durante la infancia.
- $(1 - \text{occupancy}_{\text{child}})$ representa el margen físico disponible en la calzada.
- $K = 0.25$ alinea las expectativas objetivo con referencias empíricas de sistemas adaptativos del mundo real (SCATS / SCOOT: $10\%\text{--}15\%$).
- $\delta^*$ se restringe de forma segura a $[3.0\%, 25.0\%]$ para evitar metas de promoción inalcanzables en redes saturadas o promociones prematuras en corredores sin congestión.

### 5.4 Balance Físico de la Función de Recompensa (Física de Tráfico HCM)
CARINA equilibra la función de recompensa multiobjetivo para evitar la disparidad dimensional entre penalizaciones de demora y bonificaciones de flujo:

$$R(t) = w_{\text{wait}} \times T_{\text{wait}}(t) + w_{\text{flow}} \times F_{\text{discharged}}(t)$$

Según las formulaciones del Highway Capacity Manual (HCM), evacuar un vehículo ahorra el tiempo de viaje característico del tramo:

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$

El algoritmo de balance físico en [`RewardWeightsCalculator`](../../src/engine/reward_weights_calculator.py) establece:
- $w_{\text{wait}} = -1.0$ (penalización normalizada de demora por segundo de cola).
- $w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$, asegurando que los incentivos de evacuación vehicular igualen la escala de demora acumulada en cola.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
