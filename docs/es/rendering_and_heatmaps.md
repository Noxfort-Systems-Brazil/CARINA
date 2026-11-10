---
tags: [renderizado, mapas-calor, mapas, sumo, visualizacion, graficos]
aliases: [Motor de Renderizado, Mapas de Calor, Generador de Mapas, Visualización en Canvas]
---

# 🗺️ Motor de Renderizado de Mapas y Mapas de Calor Asíncronos

Este documento especifica el subsistema de renderizado cartográfico y visualización de tráfico de CARINA ubicado en [`src/rendering/`](../../src/rendering). Detalla la generación estática de mapas vectoriales desde definiciones de red vial de SUMO (`.net.xml`), la proyección espacial de coordenadas y la interpolación asíncrona de mapas de calor en tiempo real.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🖥️ Ver [UI y Panel de Control](ui_and_dashboard.md) | 📈 Ver [MFD y Analítica](mfd_and_analytics.md)

---

## 1. Arquitectura del Subsistema

CARINA proporciona visualización geoespacial nativa sin depender de teselas de mapas web externas ni de servicios de cartografía propietarios. El subsistema de renderizado opera de forma completamente offline:

```text
 Red Vial SUMO (`.net.xml`) / Telemetría
                      │
                      ▼
        ┌───────────────────────────┐
        │  map_coordinate_generator │ (Transforma UTM/Cartesianas -> Píxeles Canvas)
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│   static_map_renderer  │  │ async_heatmap_renderer │
│ (Vías, Nodos, Semáfor) │  │ (Densidad KDE y Retraso│
└───────────┬────────────┘  └───────────┬────────────┘
            │                           │
            └─────────────┬─────────────┘
                          ▼
            Superficie Nativa de Canvas Flet
                 (`LiveCanvasMapWidget`)
```

---

## 2. Módulos Centrales en `src/rendering/`

### 2.1 Transformación de Coordenadas (`map_coordinate_generator.py`)
Ubicado en [`src/rendering/map_coordinate_generator.py`](../../src/rendering/map_coordinate_generator.py):
- Convierte proyecciones de coordenadas 2D de SUMO $(x, y)$ en coordenadas de canvas del viewport $(u, v)$.
- Soporta desplazamiento suave (pan), zoom por pellizco y centrado automático basado en la caja delimitadora (bounding box) de todas las intersecciones activas.
- Gestiona la preservación de la relación de aspecto a través de monitores con diferentes resoluciones.

### 2.2 Renderizador de Mapa Vectorial Estático (`static_map_renderer.py`)
Ubicado en [`src/rendering/static_map_renderer.py`](../../src/rendering/static_map_renderer.py):
- Analiza la geometría de carriles, límites de cruces y conexiones internas desde el archivo `.net.xml` de SUMO.
- Renderiza vías arteriales multicarril con líneas divisorias, flechas de sentido y símbolos de cabezales semafóricos.
- Almacena en memoria las rutas vectoriales renderizadas para eliminar recálculos de CPU durante escenas estáticas.

### 2.3 Renderizador de Mapas de Calor Asíncrono (`async_heatmap_renderer.py`)
Ubicado en [`src/rendering/async_heatmap_renderer.py`](../../src/rendering/async_heatmap_renderer.py):
- Emplea **Estimación de Densidad de Kernel (KDE)** para interpolar mapas de calor espaciales continuos a partir de métricas discretas de carriles:
  - **Mapa de Calor de Densidad de Tráfico:** Muestra la acumulación de vehículos por kilómetro cuadrado.
  - **Mapa de Calor de Tiempos de Espera y Demoras:** Destaca cuellos de botella en vías arteriales.
  - **Mapa de Calor de Riesgo de Desbordamiento (Spillback):** Visualiza las ondas de congestión previstas por el Agente Guardian.
- Descarga el desenfoque gaussiano y las convoluciones matriciales a hilos de trabajo en segundo plano, evitando pérdidas de fotogramas en la interfaz gráfica.

---

## 3. Configuración y Gradientes de Color del Mapa de Calor

Las ponderaciones y umbrales de los mapas de calor se configuran en [`config/settings.ini`](../../config/settings.ini):

```ini
[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_flow = 1.0
saturation_threshold = 0.85
lane_aggregation_strategy = max
heatmap_strategy = combined
heatmap_saturation = 1.0
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
