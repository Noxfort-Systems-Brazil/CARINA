---
tags: [ui, flet, dashboard, frontend, sds, planificacion, widgets]
aliases: [Arquitectura de UI, Servicio Dashboard, Frontend Flet, Vista de Planificación]
---

# 🖥️ Arquitectura de UI, Vista de Planificación y Smart Dashboard Service

Este documento especifica la interfaz de usuario de escritorio nativa de CARINA ubicada en [`ui/`](../../ui), el **Smart Dashboard Service (SDS)** en [`src/sds/`](../../src/sds), el **Gestor de la Bandeja del Sistema (Tray)** y el sistema de bloqueo de instancia única.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🗺️ Ver [Renderizado y Mapas de Calor](rendering_and_heatmaps.md) | 🔍 Ver [IA Explicable y SAS](xai_and_sas.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Arquitectura de Escritorio Desacoplada (`ui/` y `src/sds/`)

Para evitar que el renderizado de la interfaz gráfica o las latencias de sockets de clientes degraden las tramas de control de tráfico en tiempo real, CARINA desacopla completamente su frontend en el proceso **`DashboardService` (SDS)** ([`run_sds_worker`](../../src/sds/dashboard_worker.py), ejecutándose con `CARINA_GATEWAY_ROLE=remote`):

```text
CentralController (owner) ──> [Cola sds] ──> DashboardService (SDS) ──> [Cola ui_telemetry] ──> Flet UI (Hilo Principal)
                                                    ├──> Servidor WebSocket (puerto 8080, timeout 2.0s y backpressure)
                                                    └──> CCOBroadcastClient (HTTPS Fijado -> Go Web Gateway :2201)
```

- **Guardas de Rendimiento y Memoria (`ui/` y `src/sds/`):**
  - [`MapAnimator`](../../ui/animators/map_animator.py) y [`WindowManager`](../../ui/managers/window_manager.py): Pausan los bucles de redibujo del mapa cuando la ventana de escritorio está minimizada u oculta (`_carina_window_hidden`) y controlan los renderizados mediante banderas `_data_dirty`.
  - [`AuditLogWidget`](../../ui/widgets/audit_log_widget.py): Pagina los registros de auditoría del Guardian ($\le 100$ filas por página) para mantener instantáneas las actualizaciones de tablas en Flet.
  - [`RemoteGatewaySettingsPersister`](../../ui/controllers/remote_gateway_settings_persister.py): Sincroniza `gateway_enabled` entre `settings.ini`, `SettingsManager`, `.env` y el backend en tiempo de ejecución.
  - [`EVPFleetConnectionCard`](../../ui/cards/evp_fleet_connection_card.py): Da de baja los escuchas de `EVPNotifier` de forma determinista en `will_unmount()`.
  - [`DashboardDataCoordinator`](../../ui/controllers/dashboard_data_coordinator.py): Actualiza los espejos pasivos locales de `HardwareConnectionManager` (`remote_hardware_status`) a partir de las tramas de telemetría IPC.

---

## 2. Arquitectura Real de la UI en Flet y Jerarquía de Vistas

El frontend está desarrollado sobre **[Flet](https://flet.dev/)** (motor Python + Flutter) ubicado en [`ui/`](../../ui).

```text
ui/
├── main_ui.py                      # Arranque principal de Flet y configuración de ventana
│
├── views/                          # Vistas de Pantalla de la Aplicación
│   ├── dashboard_view.py           # Monitoreo de tráfico en tiempo real y canvas de mapa interactivo
│   ├── planning_view.py            # Planificación topológica de red, tiempos de fase y agrupamiento
│   ├── diagnostics_view.py         # Métricas de latencia IPC, uso de memoria y monitores de procesos
│   ├── system_status_view.py       # Estado de microservicios activos y controladores físicos
│   ├── settings_view.py            # Configuración del sistema y editor de endpoints IP de controladores
│   └── error_view.py               # Captura global de errores y vista diagnóstica de excepciones
│
├── cards/                          # Tarjetas Modulares de Ajustes e Inspección (Patrón OCP)
│   ├── evp_fleet_connection_card.py    # Registro de vehículos de emergencia y config RFID/transpondedores
│   ├── evp_safety_parameters_card.py  # Compuertas de preempción, watchdog de permanencia y despejes
│   ├── remote_gateway_card.py          # Conmutadores del Gateway Go, puerto 2201 y estado de Tailscale
│   ├── account_settings_card.py        # Perfil de usuario operador, roles (RBAC) y credenciales
│   ├── database_settings_card.py       # Selección de motor de BD (SQLite/PostgreSQL) y migraciones
│   ├── hardware_connection_card.py     # Pool de conexiones a controladores de campo NTCIP 1202 y UTMC
│   ├── piloting_school_card.py         # Ritmo autónomo PBT y umbrales de graduación de RL
│   ├── reward_weights_card.py          # Balanceo de recompensas de demora, presión, cola y velocidad
│   ├── traffic_rules_card.py           # Restricciones de verde mínimo, despeje de amarillo y todo-rojo
│   ├── yellow_schedule_card.py         # Horarios automatizados de destello amarillo nocturno
│   ├── monitor_settings_card.py        # Telemetría hacia broker MQTT externo o webhook HTTP
│   ├── advanced_system_card.py         # Timeouts de Watchdog, tamaños de búfer IPC y latidos
│   ├── advanced_dqn_card.py            # Tamaño de replay buffer DQN, sincronización y epsilon
│   └── advanced_ppo_card.py            # Ratio de recorte PPO, coeficiente de entropía y pérdida
│
├── widgets/                        # Widgets Modulares Especializados de UI
│   ├── live_canvas_map_widget.py   # Canvas personalizado de alto rendimiento para vías y semáforos
│   ├── evp_vehicle_marker.py       # Renderizador custom para vehículos de emergencia (formas y sirenas)
│   ├── evp_vehicle_card.py         # Tarjeta flotante con telemetría GPS en tiempo real, velocidad y ETA
│   ├── planning_control_panel_widget.py # Barras de herramientas de planificación e inspector de nodos
│   ├── mfd_viewer_widget.py        # Trazador de curvas en vivo del Diagrama Fundamental Macroscópico
│   ├── xai_viewer_widget.py        # Gráficos de atribución de características neuronales con Captum
│   ├── street_info_widget.py       # Lecturas por carril de velocidad, ocupación y longitud de cola
│   ├── traffic_light_widget.py     # Animaciones de cabezales semafóricos en vivo (Rojo, Amarillo, Verde)
│   ├── audit_log_widget.py         # Tabla pericial de inspección de vetos de seguridad del Guardian
│   └── global_controls_widget.py   # Botones de Iniciar, Pausar, Paso a Paso y Anulación de Emergencia
│
├── renderers/                      # Dibujo en Canvas y Sincronización Visual
│   ├── map_drawer.py               # Rasterizador de geometría vectorial para carriles e intersecciones
│   ├── planning_map_renderer.py    # Motor de disposición visual para nodos topológicos
│   └── map_visual_syncer.py        # Sincronizador de animación fluida a 60 FPS
│
└── locales/                        # Diccionarios de Internacionalización (i18n)
    ├── pt_br.json                  # Portugués (Brasil) - Predeterminado
    ├── en_us.json                  # Inglés (Estados Unidos)
    ├── es_es.json                  # Español
    ├── fr_fr.json                  # Francés
    ├── ru_ru.json                  # Ruso
    └── zh_cn.json                  # Chino Simplificado
```

---

## 3. Vista de Planificación y Editor de Topología de Red

La **Vista de Planificación** ([`ui/views/planning_view.py`](../../ui/views/planning_view.py)) permite a los ingenieros de tráfico inspeccionar y configurar de forma interactiva las redes viales:
- **Agrupamiento Topológico:** Agrupa conglomerados de intersecciones en corredores arteriales coordinados (Ondas Verdes).
- **Inspector de Fases y Etapas:** Inspecciona restricciones de verde mínimo, despeje de amarillo y búferes todo-rojo entre verdes.
- **Manejador de Exportación:** Exporta planes de tiempos de señales modificados directamente hacia los repositorios de controladores o plantillas CSV.

Para detalles del renderizado de mapas vectoriales, consulte [Renderizado de Mapas y Mapas de Calor](rendering_and_heatmaps.md).

---

## 4. Bandeja del Sistema y Bloqueo de Instancia Única (`SingleInstanceLock`)

CARINA se ejecuta de manera transparente como un demonio de fondo en el sistema con un icono nativo en la bandeja de escritorio:

### 4.1 Gestión de Bandeja del Sistema ([`UITrayManager`](../../src/launcher/ui_tray_manager.py))
- **Acciones de Bandeja:** Minimizar a Bandeja, Abrir Panel de Control, Ver Registros en Vivo, Reiniciar Servicios, Apagado Seguro.
- **Notificaciones Emergentes:** Emite notificaciones nativas del SO cuando el Watchdog detecta caídas de microservicios o cuando el Agente Guardian ejecuta un veto de seguridad de emergencia.

### 4.2 Bloqueo de Instancia Única ([`SingleInstanceLock`](../../src/launcher/single_instance.py))
- **Puerto:** `42123`
- Si un usuario ejecuta `carina.py` o el ejecutable mientras CARINA ya está activo:
  1. El proceso duplicado intenta enlazar el puerto TCP `42123`.
  2. Al fallar, transmite una señal de comando `RESTORE` sobre el socket TCP local a la instancia primaria.
  3. La instancia primaria trae la ventana de Flet al primer plano y el proceso duplicado finaliza limpiamente.

---

## 5. Arquitectura Modular de Tarjetas de Configuración (`ui/cards/`)

La vista de configuración de CARINA ([`ui/views/settings_view.py`](../../ui/views/settings_view.py)) sigue una Arquitectura de Componentes Abierto-Cerrado (OCP) ensamblada mediante [`SettingsConfigurator`](../../ui/builders/settings_configurator.py):

| Componente de Tarjeta | Descripción | Modos Automático / Manual |
| :--- | :--- | :--- |
| **`EVPFleetConnectionCard`** | Registro de flota de vehículos de emergencia y transpondedores RFID | • Clasificación por Corporación (Policía, SAMU, Bomberos)<br>• Autorización de Matrículas y Bloqueo de Acceso |
| **`EVPSafetyParametersCard`** | Cinemática de preempción, compuertas y despejes de seguridad | • Compuerta de Detección de Entrada ($60\text{--}160\text{ m}$)<br>• Umbral de Salida ($\le 15\text{ m}$)<br>• Watchdog de Permanencia ($45\text{ s}$)<br>• Despejes Reglamentarios Amarillo/Todo-Rojo |
| **`RemoteGatewayCard`** | Gestión del Gateway Web en Go y la malla Tailscale | • Conmutador del Demonio Web Gateway en Puerto 2201<br>• Estado de Tailscale Funnel e Inspector de URL Pública |
| **`AccountSettingsCard`** | Autenticación de operadores y perfiles de usuario RBAC | • Asignación de Roles (Admin, Operador, Auditor)<br>• Seguridad de Sesión y Credenciales JWT |
| **`DatabaseSettingsCard`** | Configuración de almacenamiento persistente SQLite y PostgreSQL | • Conmutador de Motor de BD y Configuración de Pool<br>• Verificación de Conexión y Migraciones de Esquema |
| **`PilotingSchoolCard`** | Ritmo de duración de ciclo de vida y reglas de promoción | • Regulación Automática de Duración (Tamaño de Red)<br>• Margen Dinámico de Graduación por Fluidos ($\delta^*$) |
| **`RewardWeightsCard`** | Ponderaciones de optimización RL (Tiempo de Espera vs Flujo) | • Balance Físico Automático (Tiempo de Viaje HCM $\tau$)<br>• Anulaciones Manuales de Ponderación |
| **`YellowScheduleCard`** | Horarios autónomos de destello amarillo nocturno | • Programador de Ventanas Horarias (HH:MM)<br>• Asignación Selectiva por Intersección o Red Completa |
| **`AdvancedSystemCard`** | Parámetros del sistema, PBT y Watchdog | • Percentil de Explotación PBT<br>• Período de Gracia de Watchdog e Intervalos de Análisis |
| **`AdvancedDQNCard`** | Hiperparámetros de Deep Q-Network | • Capacidad de Replay Buffer, Sincronización Red Objetivo, $\epsilon$-decay |
| **`AdvancedPPOCard`** | Hiperparámetros de Proximal Policy Optimization | • Ratio de Recorte ($\epsilon=0.2$), Coeficiente de Entropía y Pérdida de Valor |
| **`TrafficRulesCard`** | Tiempos semafóricos mínimos y normas reglamentarias | • Verde Mínimo, Despeje de Amarillo, Búferes Todo-Rojo |
| **`HardwareConnectionCard`** | Controladores físicos de campo (NTCIP / UTMC) | • Endpoints IP, Credenciales SNMP y Prueba Fail-Safe |
| **`MonitorSettingsCard`** | Streaming telemétrico y de incidentes externo | • Endpoints para Broker MQTT o Webhook HTTP |

---

## 6. Marcadores Visuales de Canvas EVP e Inspector de Telemetría en Vivo (`ui/widgets/`)

Para la monitorización de escritorio, CARINA renderiza vehículos de emergencia activos en tiempo real directamente sobre el canvas interactivo de Flet:

- **`EVPVehicleMarker` ([`ui/widgets/evp_vehicle_marker.py`](../../ui/widgets/evp_vehicle_marker.py)):**
  - **Glifos por Corporación:** Renderiza siluetas vectoriales diferenciadas según la corporación:
    - *Ambulancia / SAMU:* Triángulo Equilátero ($\Delta$, Blanco `#FFFFFF` / Rojo Alerta `#E53935`).
    - *Bomberos / Bombeiros:* Cuadrado ($\square$, Naranja `#FF9800`/`#FF8C00` / Rojo Fuego `#FF3D00`).
    - *Policía / Tránsito:* Círculo ($\bigcirc$, Azul Oscuro `#1E3A8A` / Azul Real `#2563EB`).
  - **Animador de Sirena:** Cuando `siren_active=True`, el marcador genera anillos estroboscópicos concéntricos pulsantes a $2.5\text{ Hz}$ en el canvas, alertando a los operadores sobre una atención de emergencia en curso.
  - **Rumbo Dinámico:** Rota automáticamente la orientación del vehículo para reflejar los grados de rumbo GPS en tiempo real.

- **`EVPVehicleCard` ([`ui/widgets/evp_vehicle_card.py`](../../ui/widgets/evp_vehicle_card.py)):**
  - Tarjeta HUD superpuesta flotante que muestra indicativo de llamada, velocidad ($\text{km/h}$), estado de sirena, distancia a la línea de detención del semáforo ($\text{m}$) y estado de preempción (`APPROACHING`, `HOLD_ACTIVE`, `CLEARED`).

---

## 7. Arquitectura Web y Móvil del Centro de Control Operativo (CCO) (`src_tsx/src_cco`)

Además de la interfaz nativa en Flet, CARINA incluye una moderna plataforma web para el **Operador del Centro de Control (CCO)** desarrollada con **React 18**, **TypeScript**, **TailwindCSS** y **Vite** ubicada en [`src_tsx/src_cco/`](../../src_tsx/src_cco). Diseñada bajo los principios de **Clean Architecture**, garantiza el desacoplamiento total entre las reglas de dominio de tráfico, la infraestructura de streaming y los componentes de presentación:

```text
src_tsx/src_cco/
├── domain/                         # Entidades Puras de Dominio, Modelos y Servicios de Negocio
│   ├── models/                     # Entidades Centrales de Negocio
│   │   ├── Topology.ts             # Interfaces MapTopology, Node, Edge, Bounds
│   │   ├── CongestionLevel.ts      # VO de dominio que resuelve umbrales y colores de retención
│   │   ├── EmergencyVehicle.ts     # Modelo de estado de telemetría y preempción (SAMU, Bomberos, Policía)
│   │   └── TrafficLight.ts         # Modelos de cabezales de fase, estado de indicación y tiempos
│   ├── services/                   # Servicios Geométricos y Cartográficos Puros
│   │   ├── MapProjectionService.ts # Cálculo de límites ortográficos 2D isotrópicos y relación de aspecto SVG
│   │   ├── GeoProjectionService.ts # Conversión canónica de GPS WGS84 a coordenadas cartesianas SUMO
│   │   └── StreetTopologyGrouperService.ts # Agrupación de aristas y generación de trazados de mapa de calor
│   └── contracts/                  # Interfaces de Límite (DIP)
│       ├── ITopologyRepository.ts  # Contrato de obtención de topología de red
│       └── ICcoStreamService.ts    # Interfaz de streaming en tiempo real y estado de conexión
│
├── application/                    # Casos de Uso de la Aplicación y Orquestadores
│   └── usecases/
│       ├── LoadTopologyUseCase.ts          # Obtiene y almacena en caché la geometría de la red
│       ├── ManageEmergencyFleetUseCase.ts   # Clasifica vehículos por corporación y calcula alertas activas
│       └── ProcessTelemetryUseCase.ts      # Desempaqueta tramas SSE en el estado del dominio
│
├── infrastructure/                 # Adaptadores Externos, APIs y Gateways
│   ├── api/
│   │   └── HttpTopologyRepository.ts       # Implementación Axios/Fetch de ITopologyRepository
│   ├── stream/
│   │   └── SseCcoStreamService.ts          # Cliente Server-Sent Events (/cco/stream) con autoreconexión
│   └── adapters/
│       └── EChartsOptionAdapter.ts         # Adaptador que transforma modelos de dominio en opciones ECharts
│
└── presentation/                   # UI Reactiva, Hooks, Componentes y Temas
    ├── context/
    │   └── ThemeContext.tsx                # Conmutador de tema de turno operativo (☀️ Claro / 🌙 Oscuro) con localStorage
    ├── utils/
    │   └── haptics.ts                      # Retroalimentación háptica por vibración para pantallas táctiles móviles
    ├── hooks/
    │   ├── useCcoViewModel.ts              # View-model raíz coordinando casos de uso, stream SSE y estado
    │   ├── useCcoMapLayers.ts              # Cálculo memoizado de capas (calles, nodos, semáforos)
    │   └── useMapViewport.ts               # Gestos de desplazamiento, zoom, pellizco y animaciones fluidas flyTo
    ├── components/
    │   ├── CcoHeader.tsx                   # Barra responsiva con insignias de flota, búsqueda, tema y pantalla completa
    │   ├── CcoMap.tsx                      # Mapa vectorial SVG de alto rendimiento con paneo/zoom isotrópico
    │   ├── EvpAlertToast.tsx               # Notificación emergente colapsable de alerta de emergencia (micro-píldora móvil)
    │   └── map/
    │       ├── InspectionBottomSheet.tsx   # Panel inferior ergonómico para móvil e inspector flotante en escritorio
    │       ├── QuickSearchModal.tsx        # Paleta de comandos de búsqueda instantánea y autoenfoque (flyTo)
    │       ├── MapScaleBar.tsx             # Escala métrica dinámica (m/km) calibrada con precisión a SUMO
    │       ├── MapRoadsLayer.tsx           # Rasterizador de calzadas con mapa de calor de congestión
    │       ├── MapIntersectionsLayer.tsx   # Nodos de intersección interactivos con áreas de toque optimizadas
    │       ├── MapTrafficLightsLayer.tsx   # Cabezales de fase semafórica con halo brillante de diagnóstico
    │       ├── MapEmergencyVehiclesLayer.tsx # Marcadores de vehículos en vivo, rotación de rumbo y auras de sirena
    │       ├── MapGlowFilters.tsx          # Definiciones de filtros SVG de resplandor neón para señales y alertas
    │       ├── MapLegend.tsx               # Leyenda operativa colapsable para mapas de calor y glifos
    │       └── MapZoomControls.tsx         # Controles de zoom isotrópico y recentrado de cámara
    ├── styles/
    │   ├── flet_color_palette.json         # Sincronización cromática exacta con la paleta de Flet
    │   └── index.css                       # Directivas Tailwind y bloqueo de sobre-desplazamiento de viewport
    ├── App.tsx                             # Componente raíz con ThemeProvider y orquestación de modales
    └── main.tsx                            # Punto de entrada React DOM
```

---

## 8. Capacidades de UI/UX y Ergonomía del CCO Moderno

El frontend del CCO está diseñado para brindar una experiencia operacional óptima tanto en videowalls de salas de control 4K como en teléfonos inteligentes en el campo:

1. **Panel Inferior Móvil Ergonómico (`InspectionBottomSheet.tsx`):**
   - En pantallas móviles (`< 768px`), las tarjetas de inspección se anclan a la parte inferior con barra de agarre y gestos nativos de deslizamiento hacia abajo para cerrar.
   - En estaciones de trabajo de escritorio (`>= 768px`), los detalles flotan en un HUD compacto en la esquina.
   - Diagnósticos en tiempo real para:
     - **Vehículos de Emergencia:** Indicativo, velocidad ($\text{km/h}$), rumbo GPS ($^\circ$), estado de sirena e intersección de destino.
     - **Semáforos:** ID del semáforo, fase activa, indicador en vivo (Verde, Amarillo, Rojo), coordenadas y estado de supervisión de Fenix Watchdog.
     - **Intersecciones y Calles:** Nodos físicos, nombre de calle, porcentaje de congestión ($0\text{--}100\%$) y tasa de flujo.

2. **Doble Tema de Turno Operativo (☀️ Día / 🌙 Noche):**
   - **Modo Cartográfico Día (`#F7F7F7`):** Fondo claro de alto contraste optimizado para campo y luz diurna directa.
   - **Modo Videowall Noche (`#020617`):** Paleta oscura profunda concebida para reducir la fatiga visual en centros de comando nocturnos.
   - Conmutable al instante con persistencia automática en `localStorage`.

3. **Búsqueda Rápida y Autoenfoque Cinemático (`QuickSearchModal.tsx` y `flyTo`):**
   - Accesible vía botón de búsqueda o atajos de teclado globales (`Ctrl+K` o `/`).
   - Indexa al instante vehículos, semáforos, cruces y nombres de avenidas.
   - Al seleccionar un resultado se dispara un vuelo de cámara animado (`flyTo`) con interpolación cúbica suavizada.

4. **Barra de Escala Métrica Dinámica (`MapScaleBar.tsx`):**
   - Barra métrica en tiempo real (ej. `|—— 100 m ——|`) que se recalibra dinámicamente según el nivel de zoom y las coordenadas métricas 1:1 de SUMO.

5. **Filtrado Interactivo de Flota con Micro-Chips:**
   - Insignias interactivas para **SAMU**, **Bomberos** y **Policía**. Al pulsar una corporación se resaltan sus unidades mientras se atenúan suavemente las demás.

6. **Pantalla Completa Inmersiva y Respuesta Háptica Móvil:**
   - Botón de pantalla completa para maximizar el área de visualización en videowalls.
   - Micro-vibraciones hápticas (`navigator.vibrate`) que proporcionan confirmación táctil al interactuar con semáforos, vehículos y botones de zoom en dispositivos compatibles.

---

## 9. Entrega del Gateway Web en Go, Optimizaciones CCO y Conectividad Remota

El CCO web es servido por el **Gateway Web en Go** ([`src_go/web_gateway/`](../../src_go/web_gateway)) de alto rendimiento ejecutándose en el puerto `2201` (`CARINA_GATEWAY_PORT`):

- **Entrega *Fail-Closed* y Protegida por Token:** Responde `503 Service Unavailable` cuando está deshabilitado (`gateway_enabled=False`), sirve activos estáticos comprimidos de React en `/cco/` y protege `/cco/stream`, `/cco/topology` y `/cco/broadcast` con `CARINA_CCO_AUTH_TOKEN` en tiempo constante, CORS `CARINA_CCO_ALLOWED_ORIGIN` y HTTPS/TLS opcional.
- **Optimizaciones de Hilo de Compositor y Viewport (`src_tsx/src_cco/`):** Utiliza animaciones CSS por keyframes exclusivas del compositor GPU (`transform` + `opacity`), paneo/zoom guiado por referencias `requestAnimationFrame` en `useMapViewport.ts`, diferenciación de estado por igualdad superficial (*shallow equality*) en `useCcoViewModel.ts` y pausa de temporizadores de limpieza vehicular cuando `document.hidden` es verdadero.
- **Stream de Telemetría SSE Sub-50ms e Ingestión Fijada (*Pinned*):** Expone `/cco/stream` alimentado por [`CCOBroadcastClient`](../../src/sds/cco_broadcast_client.py) de SDS (publicador no bloqueante *latest-wins* con fijación SHA-256 de certificado hoja mediante `PinnedHTTPSConnection`).
- **Malla Tailscale e Ingestión Remota:** Se integra con Tailscale Funnel para acceso remoto cifrado de unidades de campo e ingestión vía webhooks desde despachos CAD de emergencias.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
