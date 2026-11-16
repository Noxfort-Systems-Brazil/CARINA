---
tags: [mfd, analitica, dinamica, densidad, gating, capacity-drop]
aliases: [Motor MFD, Analítica de Red, Física del Tráfico, Diagrama Fundamental Macroscópico]
---

# 📈 Diagrama Fundamental Macroscópico y Analítica de Red

Este documento detalla el subsistema del Diagrama Fundamental Macroscópico ubicado en [`src/mfd/`](../../src/mfd), el proceso **`MFD_Worker`**, la física del flujo macroscópico de tráfico, los algoritmos de dosificación perimetral (*perimeter gating*) y la caché del filtro de incidentes.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 📊 Ver [Criterios de Tráfico](traffic_engineering_warrants.md) | 🧠 Ver [Formulaciones Neuronales](research_notes.md)

---

## 1. Teoría del Diagrama Fundamental Macroscópico (MFD)

El **Diagrama Fundamental Macroscópico (MFD)** relaciona la acumulación total de vehículos (densidad $K$) en una red urbana con el flujo medio espacial total ($Q$). A diferencia de los modelos microscópicos que rastrean interacciones individuales de seguimiento vehicular (*car-following*), el MFD ofrece una representación holística a nivel de toda la red sobre los estados del tráfico urbano.

```text
       Q (veh/h)
          ▲                Zona 1: No Congestionada (PPO Táctico Activo)
     Qmax │           /\   Zona 2: Caída de Capacidad (Dosificación Perimetral Disparada)
          │          /  \  Zona 3: Bloqueo / Colapso (Anulación de Emergencia)
          │         /    \
          └────────┴──────┴────────► K (veh/km)
                  Kcrit   Kjam
```

- **Zona 1: Región No Congestionada ($K < K_{crit}$):** Las intersecciones individuales operan con políticas locales PPO-TCN maximizando la asignación de verde local.
- **Zona 2: Región de Caída de Capacidad (*Capacity Drop*) ($K > K_{crit}$):** La fricción vehicular entre colas provoca que el rendimiento global se degrade bruscamente (*Capacity Drop*).
- **Zona 3: Bloqueo (*Gridlock*) ($K \to K_{jam}$):** Congestión arterial generalizada donde los vehículos no pueden cruzar las intersecciones debido al desbordamiento (*spillback*) aguas abajo.

---

## 2. Formulaciones Matemáticas

La densidad a nivel de red $K_{net}$ y el flujo medio espacial $Q_{net}$ se agregan como promedios ponderados a lo largo de todos los $N$ segmentos viales monitoreados:

$$K_{net} = \frac{\sum_{i=1}^N k_i \cdot L_i}{\sum_{i=1}^N L_i}, \quad Q_{net} = \frac{\sum_{i=1}^N q_i \cdot L_i}{\sum_{i=1}^N L_i}$$

Donde:
- $k_i$: Densidad del tramo $i$ (vehículos por kilómetro).
- $q_i$: Tasa de flujo del tramo $i$ (vehículos por hora).
- $L_i$: Longitud física del tramo $i$ en metros.

---

## 3. Módulos Centrales en `src/mfd/`

La suite analítica de MFD consta de 35 módulos especializados en [`src/mfd/`](../../src/mfd):

### 3.1 Proceso MFD Worker (`mfd_worker.py`)
Se ejecuta como un proceso aislado del sistema operativo iniciado por `ProcessManager` con `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` y `OPENBLAS_NUM_THREADS=1`. Escucha en la cola IPC `mfd_trigger`, analiza redes SUMO mediante la caché LRU [`read_sumo_net_cached()`](../../src/utils/sumo_net_cache.py), renderiza curvas fuera de pantalla (*offscreen*) mediante [`mpl_utils.py`](../../src/rendering/mpl_utils.py), ejecuta la narración SLM bajo [`slm_process_lock()`](../../src/slm/slm_lock.py) con `unload()` explícito y retorna resultados en `mfd_results`.

### 3.2 Motor de Comparación y Gestor de Línea Base (`mfd_comparison_engine.py` y `mfd_baseline_manager.py`)
- Compara continuamente el rendimiento actual de la IA adaptativa frente a las curvas de línea base de tiempo fijo.
- Calcula el ahorro de vehículos-horas recorridos (VHT) y vehículos-kilómetros recorridos (VKT).

### 3.3 Reconstructor Histórico (`mfd_history_reconstructor.py`)
Reconstruye gráficos de dispersión de flujo-densidad desde `synapse_fluid_dynamics` en PostgreSQL a lo largo de ventanas de observación de múltiples días.

### 3.4 Calculador de Impacto Urbano (`mfd_impact_calculator.py`)
Cuantifica las reducciones de emisiones municipales ($\text{CO}_2$, $\text{NO}_x$), el ahorro de combustible y las ganancias de productividad económica resultantes de la mitigación de la congestión.

---

## 4. Actuación por Dosificación Perimetral (Perimeter Gating)

Cuando la densidad de la red supera la capacidad crítica ($K_{net} \ge K_{crit}$):
1. El `MFD_Worker` emite una alerta de dosificación perimetral al `CentralController`.
2. Las intersecciones perimetrales limítrofes con el núcleo urbano congestionado reducen los tiempos de verde entrante ($T_{verde} \leftarrow T_{verde} \times \eta$, donde $\eta \in [0.6, 0.8]$).
3. Los corredores arteriales de salida reciben máxima prioridad de verde para desalojar los vehículos del centro financiero y áreas densas.

---

## 5. Caché de Depuración del Filtro de Incidentes (`.carina_incident_filter_cache.json`)

Para evitar que siniestros viales localizados o cierres de carriles por obras corrompan la curva macroscópica del MFD, [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py) aísla los tramos anómalos y almacena los estados de incidentes activos en `.carina_incident_filter_cache.json` para una rápida recuperación entre reinicios del sistema.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
