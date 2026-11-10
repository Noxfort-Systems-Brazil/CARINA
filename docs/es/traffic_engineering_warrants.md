---
tags: [justificaciones, mutcd, fhwa, ingenieria-trafico, seguridad, analisis, sas]
aliases: [Criterios de Ingeniería de Tráfico, Justificaciones Semafóricas, Análisis MUTCD, Evaluador de Criterios]
---

# 🚦 Criterios de Ingeniería de Tráfico Semafórico y Análisis de Infraestructura

Este documento especifica el subsistema de análisis de justificaciones técnicas de CARINA ubicado en [`src/analysis/`](../../src/analysis). Detalla la formulación matemática y la evaluación automatizada de los criterios formales de semaforización basados en el **FHWA MUTCD** (Manual on Uniform Traffic Control Devices) y normativas municipales de ingeniería de tránsito.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 📈 Ver [MFD y Analítica](mfd_and_analytics.md) | 🔍 Ver [IA Explicable y SAS](xai_and_sas.md)

---

## 1. Evaluación Automatizada de Criterios Semafóricos

Antes de instalar o modificar semáforos, los ingenieros municipales están obligados legalmente a demostrar que una intersección cumple con criterios técnicos formales de justificación. El **Smart Analysis System (SAS)** evalúa los datos históricos acumulados en PostgreSQL para determinar si la semaforización está justificada o si requiere modificaciones en sus planes de tiempos.

```text
 Datos Históricos de Tráfico (PostgreSQL `synapse_fluid_dynamics`)
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
   │(Estrategias Criterio)│      │(Matemática Vol y Vel)│
   └──────────┬───────────┘      └──────────────────────┘
              │
              ├──> Criterio 1: VolumeWarrant (Volúmenes Tabla MUTCD 4C-1)
              ├──> Criterio 2: DelayWarrant (Demora Inaceptable D)
              ├──> Criterio 3: QueueWarrant (Fila Estadística P95)
              └──> Criterio 4: SaturationWarrant (Grado de Saturación X = v/c)
```

---

## 2. Estrategias de Criterios Implementadas (`src/analysis/warrant_strategies.py`)

CARINA estructura su análisis de ingeniería mediante el **Patrón Strategy** registrado en [`WarrantEvaluator`](../../src/analysis/warrant_evaluator.py):

### 2.1 Criterio 1: Criterio de Volumen (`VolumeWarrant`)
Evalúa los volúmenes de aproximación utilizando la ecuación fundamental del flujo vehicular:
$$q = k \times (v \times 3.6)$$
- **Umbrales de la Tabla 4C-1 del MUTCD:** Evalúa carriles de aproximación y límites de velocidad:
  - **1 Carril Principal / 1 Carril Secundario:** Condición A: $V_{principal} \ge 500\text{ veh/h}$, $V_{secundario} \ge 150\text{ veh/h}$. Condición B: $V_{principal} \ge 750\text{ veh/h}$, $V_{secundario} \ge 75\text{ veh/h}$.
  - **2+ Carriles Principal / 2+ Carriles Secundario:** Condición A: $V_{principal} \ge 600\text{ veh/h}$, $V_{secundario} \ge 200\text{ veh/h}$. Condición B: $V_{principal} \ge 900\text{ veh/h}$, $V_{secundario} \ge 100\text{ veh/h}$.
- **Factor de Reducción del 70% por Alta Velocidad:** Si la velocidad reglamentaria de la vía principal supera los $70\text{ km/h}$ ($19.44\text{ m/s}$), todos los umbrales de volumen se escalan por $0.70$ (ej., $500 \to 350\text{ veh/h}$, $150 \to 105\text{ veh/h}$).

### 2.2 Criterio 2: Criterio de Demora (`DelayWarrant`)
Cuantifica la demora operacional experimentada en accesos secundarios respecto al tiempo de viaje en flujo libre:
$$D = \frac{L}{v_{\text{real}}} - \frac{L}{v_{\text{limite}}}$$
- Evalúa si la demora promedio supera el umbral de demora inaceptable:
$$D_{prom} > D_{\text{umbral}}$$
- Umbral predeterminado: `unacceptable_delay = 90.0 s`.

### 2.3 Criterio 3: Criterio de Fila P95 (`QueueWarrant`)
Audita la acumulación de colas utilizando distribuciones estadísticas de percentil 95 para prevenir el bloqueo aguas arriba (spillback):
- Calcula la longitud de cola empírica al percentil 95 $P95(Q)$ en las muestras de sensores acumuladas.
- El criterio se cumple si:
$$P95(Q) > Q_{\text{umbral}}$$
- Umbral predeterminado: `max_queue_p95 = 15` vehículos.

### 2.4 Criterio 4: Criterio de Grado de Saturación (`SaturationWarrant`)
Evalúa la relación volumen-capacidad ($v/c$) en todos los carriles de aproximación:
$$X = \frac{q}{N \times f_{\text{ideal}}}$$
Donde:
- $q$: Volumen medio espacial ($\text{veh/h}$).
- $N$: Número de carriles de aproximación.
- $f_{\text{ideal}}$: Flujo de saturación ideal por carril ($1800\text{ veh/h/carril}$).
- El criterio se satisface si la tasa de saturación crítica máxima supera la capacidad admisible:
$$X_{\max} > X_{\text{critico}}$$
- Umbral predeterminado: `saturation_critical = 0.85` ($85\%$ de capacidad).

---

## 3. Utilidades Matemáticas (`warrant_math.py`)

Ubicadas en [`src/analysis/warrant_math.py`](../../src/analysis/warrant_math.py):
- **`compute_volume_q(density, speed)`:** Calcula el flujo medio espacial $q = k \times (v \times 3.6)$.
- **`compute_delay(length, v_real, v_limit)`:** Calcula la demora vehicular real respecto al límite de velocidad reglamentario.
- **`compute_p95(values)`:** Calcula la longitud de cola empírica al percentil 95.
- **`compute_saturation_ratio(volume, num_lanes, ideal_flow)`:** Calcula el grado de saturación ($X = v/c$).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
