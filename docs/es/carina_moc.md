---
tags: [moc, hub, docs, obsidian, carina, index]
aliases: [CARINA MOC, Hub Maestro de Documentación, Índice de Documentación, Bóveda de Conocimiento]
---

<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA Hub Central de Documentación Técnica Maestra
### Índice Central y Bóveda de Conocimiento de la Arquitectura Multiagente
*Noxfort Systems — A State Of Art Company*

</div>

Bienvenido a la biblioteca de documentación técnica de **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture). Diseñado como un ecosistema empresarial de Aprendizaje por Refuerzo Profundo masivamente concurrente y de alta frecuencia para el control semafórico en tiempo real, CARINA conecta la IA neuro-simbólica de alto nivel, la actuación de hardware gRPC en tiempo real y el aislamiento a nivel de sistema operativo mediante multiprocesamiento.

Este índice maestro de documentación proporciona una cobertura técnica profunda para desarrolladores de núcleo, investigadores académicos, ingenieros de tráfico municipales e integradores de sistemas. Es totalmente compatible tanto con **GitHub** como con **[Obsidian](https://obsidian.md/)**.

---

## 🗺️ Mapa del Código y Jerarquía de Directorios

```text
CARINA_CORE/
├── carina.py                   # Orquestador Maestro (SingleInstanceLock, ProcessManager, UI/Tray)
├── ARCHITECTURE.md             # Esquema de Multiprocesamiento de 8 Procesos y Topología IPC
├── pyproject.toml              # Cadena de herramientas de compilación y metadatos del proyecto
├── requirements.txt            # Dependencias de ejecución en Python
├── .env.example                # Variables de entorno y credenciales para Apps de 12 Factores
│
├── config/                     # Sistemas de Configuración
│   ├── settings.ini            # Parámetros globales (IA, PBT, Watchdog, MFD, Logging)
│   ├── database/               # Consultas SQL dinámicas y esquemas (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Reglas de seguridad y consistencia semántica (safety_rules.json, semantic_rules.json)
│   └── templates/              # Plantillas multilingües de informes, MFD, SAS y XAI
│
├── packaging/                  # Empaquetado Hermético Debian y Especificaciones
│   ├── Dockerfile.build        # Constructor hermético multietapa (Node, Go, Python, dpkg-deb)
│   └── deb/                    # Archivos de control Debian, unidades systemd y scripts post-instalación
│
├── scripts/                    # Scripts de Compilación, Automatización y Pruebas con Límite de Memoria
│   ├── build_deb.sh            # Generador contenerizado de paquetes Debian
│   └── pytest_limited.sh       # Ejecutor Pytest limitado en RAM por cgroup v2 / ulimit (máx. 2 GB)
│
├── proto/                      # Especificaciones del Protocolo gRPC
│   └── synapse_hft.proto       # Definiciones Protobuf de Telemetría y Actuación de Alta Frecuencia
│
├── docs/                       # Bóveda Integral de Conocimiento
│   ├── CARINA_MOC.md           # Hub Central Maestro de Documentación (Este Archivo)
│   ├── index.md                # Portal y Punto de Entrada MkDocs
│   ├── ARCHITECTURE.md         # Esquema de Multiprocesamiento de 8 Procesos y Topología IPC
│   ├── EVP_AND_PREEMPTION.md   # Preempción de Vehículos de Emergencia, Gateway Web Go y CCO
│   ├── API_REFERENCE.md        # Protocolo gRPC Synapse HFT y Esquemas de Colas IPC
│   ├── RESEARCH_NOTES.md       # Formulaciones Matemáticas de PPO-TCN, PAE, GATv2 y DA SILVA
│   ├── HARDWARE_DRIVERS.md     # Controladores Físicos: Integración NTCIP 1202, UTMC2 y SNMP
│   ├── SAFETY_AND_WATCHDOG.md  # Firewall de Seguridad Guardian, Regras de Veto y Watchdog
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # Criterios Semafóricos MUTCD / FHWA 1, 2, 3, 4
│   ├── MFD_AND_ANALYTICS.md    # Diagrama Fundamental Macroscópico y Dinámica de Densidad de Red
│   ├── DATABASE_AND_SCHEMAS.md # Capa de Persistencia, Almacenamiento Asíncrono Delta y Esquemas SQL
│   ├── XAI_AND_SAS.md          # IA Explicable, Gradientes Integrados Captum y Analítica SAS
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # Generador Modular Word (.docx) y Ecuaciones OMML
│   ├── SLM_AND_LOCAL_LLM.md    # Integración Local de LLM Offline (Qwen3.5 2B / llama.cpp)
│   ├── UI_AND_DASHBOARD.md     # Aplicación de Escritorio Flet, Vista de Planificación y Arquitectura SDS
│   ├── RENDERING_AND_HEATMAPS.md # Renderizado Vectorial de Mapas e Interpolación Asíncrona de Heatmaps
│   ├── SECURITY_AND_AUTH.md    # Cuentas de Usuario, Hashing PBKDF2 HMAC SHA-256 con Sal y Bloqueo de Fuerza Bruta
│   ├── DEVELOPER_GUIDES.md     # Configuración del Entorno, Jerarquía de Agentes, Ajustes y Empaquetado
│   ├── TESTING.md              # Suite de Pruebas Pytest, Mocks de Controladores y Cobertura
│   └── DEPLOYMENT_AND_PACKAGING.md # Construcciones Docker, Demonios Systemd y Paquetes Debian
│
├── bin/                        # Binarios nativos compilados (carina-go)
├── src_go/                     # Gateway de Hardware y Web en Go (NTCIP, UTMC, EVP, Gateway Web)
│   ├── cmd/gateway/            # Punto de entrada del Gateway y bucle IPC stdin/stdout en NDJSON
│   ├── configs/                # Perfiles OID embebidos en JSON para NTCIP y UTMC
│   ├── evp_go/                 # Despachador de Preempción EVP en Microsegundos
│   ├── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
│   └── web_gateway/            # Gateway HTTP/SSE (Puerto 2201), Malla Tailscale y Handlers CCO
├── src_tsx/                    # Aplicación Web para el Operador del Centro de Control (CCO)
│   └── src_cco/                # React 18, TypeScript, Tailwind CSS, Capas de Mapas SVG, ECharts
├── src/                        # Código Fuente Primario en Python
│   ├── agents/                 # PPO LocalAgent, GuardianAgent, PAEStateAugmentor y Checkpoints
│   ├── analysis/               # Evaluador de Criterios MUTCD, WarrantMath y Análisis de Tráfico
│   ├── blocks/                 # Constructor modular de .docx, convertidores OMML y formateadores en caché
│   ├── central_controller.py   # Servidor de Telemetría gRPC de Alta Frecuencia y Propietario del Gateway
│   ├── communication/          # MonitorClient, Seguridad gRPC HFT (TLS/mTLS/Bearer) y ThreadSafePipe
│   ├── controller/             # HardwareGatewayCoordinator, ConnectionManager, FenixStageDispatcher y Anulaciones
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, ActionAuthorizer y PopulationManager
│   ├── database/               # DatabaseEngine, PostgresConnectionPool, SQLite WAL y StepDecisionWorker
│   ├── drivers/                # Proxy Gateway Go, RemoteHardwareDriverProxy, HardwareTelemetryDecoder y Trap Bridge
│   ├── engine/                 # StepProcessor, BatchedPAEEncoder, FleetBatchInferencer (vmap) y PhysicalActionMasker
│   ├── evp/                    # Preempción de Vehículos de Emergencia (EVPService, EVPSnapshotSynchronizer, Cinemática)
│   ├── fenix/                  # Auto-recuperación y Supervisor de Procesos F.E.N.I.X. (Supervisor, Runner, Reconciler)
│   ├── handlers/               # Manejadores de solicitudes de IA, comandos de UI y de Watchdog
│   ├── interfaces/             # Protocolos SOLID Segregados (Controller, Drivers, Engine, Repositories)
│   ├── launcher/               # ProcessManager, BackendServiceRegistry, FenixSupervisionLoop y WorkerEntrypoints
│   ├── manager/                # CycleManager, StageTransitionManager, AgentPopulationLoader y ServiceManager
│   ├── maturity/               # MaturityManager, AgentMaturity, PromotionService, Config y Port
│   ├── mfd/                    # Analizador del Diagrama Fundamental Macroscópico (MFD) y Worker
│   ├── models/                 # Backbone TCN Unificado, ActorCriticNet, iTransformer PAE, QR-D3QN y ST-GATv2 Lite
│   ├── optimizer/              # Entrenamiento Basado en Población (PBT), PPO en Host NumPy y Optimizadores DQN
│   ├── promotion/              # Calculadoras de Ritmo de Madurez, Margen de Rendimiento y Evaluación
│   ├── rendering/              # StaticMapRenderer, AsyncHeatmapRenderer y mpl_utils Offscreen
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo, HardwareConnectionRepo y ConnectionCSVStore
│   ├── safety/                 # GuardianPhysicsEstimator, GuardianRiskCalibrator (Noisy-OR), GuardianShadowTrainer y Checkpoints
│   ├── sas/                    # Smart Analysis System (Criterios de Infraestructura Offline)
│   ├── sds/                    # Smart Dashboard Service (Puente UI Flet, WebSockets y CCOBroadcastClient fijado)
│   ├── security/               # Subsistema Desacoplado de Seguridad (Auth, PBKDF2, Lockdown, Repositorios)
│   ├── settings/               # Ajustes Modulares (Interfaces SOLID, esquemas, INI y .env)
│   ├── slm/                    # Small Language Model (Qwen3.5 2B, sondeo VRAM pynvml y slm_process_lock)
│   ├── transports/             # Transportes polimórficos (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Rutas, SumoNetCache y Cálculo de Episodios
│   ├── watchdog/               # Monitor de latidos de procesos en tiempo real y fallback a fail-safe
│   └── xai/                    # Atribución Integrated Gradients, generador multiagente en caché y worker
│
├── ui/                         # Aplicación de Escritorio Nativa en Flet
│   ├── cards/                  # Tarjetas modulares de ajustes y telemetría (RemoteGateway, Hardware, EVP)
│   ├── controllers/            # DashboardDataCoordinator y RemoteGatewaySettingsPersister
│   ├── handlers/               # Manejadores de eventos, SettingsHandler y SystemTrayHandler nativo
│   ├── views/                  # DashboardView, PlanningView, DiagnosticsView, SettingsView
│   ├── widgets/                # LiveCanvasMapWidget, PlanningControlPanel, MFDViewer, AuditLogWidget Paginado
│   ├── renderers/              # PlanningMapRenderer, MapVisualSyncer, MapDrawer
│   ├── animators/              # MapAnimator (pausa en ventana oculta y control por dirty-flag)
│   └── locales/                # Diccionarios multilingües en JSON (pt_br, en_us, es_es, etc.)
│
└── tests/                      # Suite Pytest (967 Pruebas Recopiladas, memory_guard.py) + 46 Pruebas Go en src_go/
```

---

## 📖 Dimensiones del Sistema y Navegación de la Bóveda de Conocimiento

### 1. Infraestructura Central y Controladores de Hardware
- **[Inmersión en la Arquitectura](architecture.md)**: Esquema técnico exhaustivo que detalla los 8 microservicios concurrentes del SO, el aislamiento de procesos mediante `multiprocessing`, los canales IPC por Pipe/Queue y el bucle de ejecución.
- **[Controladores de Hardware y Controladores Físicos](hardware_drivers.md)**: Especificaciones del Gateway de Hardware compilado en Go (`carina-go`), tuberías estándar IPC en NDJSON, NTCIP 1202 (ASC), estándar británico UTMC / UTMC2, cliente SNMP v2c/v3, pool de conexiones y reversión determinista a fail-safe por hardware.
- **[Referencia de API y Protocolo HFT](api_reference.md)**: Especificaciones completas de la interfaz gRPC `Synapse HFT`, telemetría externa para Monitor (MQTT/HTTP), endpoints de métricas Prometheus (puerto 8001) y esquemas de colas IPC.
- **[Arquitectura de Base de Datos y Esquemas](database_and_schemas.md)**: Especificaciones de `DatabaseWorker`, `StepDecisionWorker`, pool de conexiones, configuración de 12 factores con `.env` y almacenamiento delta en PostgreSQL (97.9% de reducción).
- **[Seguridad y Autenticación](security_and_auth.md)**: Gestión de cuentas de usuario, hashing `PBKDF2 HMAC SHA-256` con sal, defensa mediante bloqueo contra ataques de fuerza bruta y control de acceso basado en roles (RBAC).
- **[Arquitectura de Ajustes Modulares](architecture.md#4-arquitectura-de-configuraciones-modulares-srcsettings)**: Subsistema de configuración SOLID desacoplando esquemas, persistencia INI y secretos `.env` bajo el estándar de 12 factores.
- **[Monitoreo Polimórfico y Transportes](architecture.md#5-arquitectura-polimorfica-de-monitoreo-y-transportes-srctransports)**: Streaming de telemetría e incidentes sobre brokers MQTT y endpoints en la nube HTTP/HTTPS REST/Ngrok.

### 2. Inteligencia Artificial y Seguridad Neuro-Simbólica
- **[Investigación Neuronal y Formulaciones](research_notes.md)**: Formulaciones matemáticas profundas para PPO-TCN, proyección latente $Z$ del Autoencoder Predictivo (PAE), flujos de valor/ventaja en Dueling DQN-TCN, Atención en Grafos ST-GATv2 Lite y el currículo de maduración DA SILVA.
- **[Arquitectura de Seguridad, Watchdog y F.E.N.I.X.](safety_and_watchdog.md)**: Inventario de reglas de Veto Simbólico (SR-00 a SR-06), umbrales de Veto Neuronal del PAE, monitorización de latidos Watchdog en tiempo real (< 500 ms) y resurrección autónoma de procesos con F.E.N.I.X. mediante reconciliación de estado limpio en los límites.
- **[IA Explicable, SAS y Analítica MFD](xai_and_sas.md)**: Detalles operativos de la canalización modular de XAI, atribución por Integrated Gradients de Captum y auditorías forenses periciales para municipios.
- **[Motor de Bloques de Informes y Generador Word](report_blocks_and_templates.md)**: Generación automatizada de informes Word (`.docx`) conformes a normativas técnicas (como ABNT NBR 14724) con fórmulas nativas de Office Math Markup Language (OMML) convertidas desde LaTeX.
- **[Modelos de Lenguaje Reducidos (SLM)](slm_and_local_llm.md)**: Inferencia local de LLM 100% offline (Qwen3.5 2B / llama.cpp) que genera explicaciones periciales en lenguaje natural sin dependencias de la nube.

### 3. Física de Tráfico, Criterios de Justificación y Gráficos
- **[Criterios de Ingeniería de Tráfico Semafórico](traffic_engineering_warrants.md)**: Evaluación automatizada de los criterios formales de justificación semafórica de la FHWA/MUTCD (Criterios 1 a 4) y justificaciones de infraestructura física.
- **[Diagrama Fundamental Macroscópico y Dinámica](mfd_and_analytics.md)**: Física de flujo-densidad en toda la red, densidad crítica ($K_{crit}$), dosificación perimetral (perimeter gating), detección de caída de capacidad (capacity drop) y almacenamiento en caché de filtros de incidentes.
- **[Renderizado de Mapas y Heatmaps](rendering_and_heatmaps.md)**: Análisis sintáctico offline de mapas vectoriales desde redes `.net.xml` de SUMO y mapas de calor continuos asíncronos mediante Estimación de Densidad de Kernel (KDE).

### 4. Interfaz de Escritorio y Operaciones
- **[UI y Servicio Smart Dashboard (SDS)](ui_and_dashboard.md)**: Desglose arquitectónico de la interfaz nativa de escritorio en Flet, vista interactiva de planificación (Planning View), bloqueo de instancia única mediante socket (puerto 42123) y streaming de telemetría por WebSockets.
- **[Guías para Desarrolladores e Integración](developer_guides.md)**: Guía práctica para configurar entornos, modificar archivos de configuración, extender agentes neuronales y compilar paquetes.
- **[Pruebas y Validación](testing.md)**: Directrices para ejecutar `pytest` (967 pruebas automatizadas en 192 módulos unitarios, 8 de integración y 4 módulos raíz + 46 pruebas en Go), limitación de RAM con `scripts/pytest_limited.sh`, mocks de controladores y validación de vetos de seguridad del Guardian.
- **[Despliegue, Empaquetado y Contenedores](deployment_and_packaging.md)**: Guía para la contenerización con Docker (`Dockerfile`), unidades de servicio en Linux Systemd y empaquetado de binarios Debian `.deb`.

### 5. Preempción de Emergencia y Operaciones Remotas (EVP / CCO)
- **[Preempción de Vehículos de Emergencia y Operaciones Remotas](evp_and_preemption.md)**: Especificaciones del motor de Preempción de Vehículos de Emergencia (EVP), cumplimiento de normativas de tráfico (CONTRAN/MUTCD), cinemática Haversine, disparador de doble factor, salvaguarda de watchdog de 45 segundos, despachador de preempción en Go, malla segura Tailscale Funnel e interfaz web para el Operador del Centro de Control (CCO) (`src_tsx/src_cco`).

---

> 💡 **Grafo de Conocimiento en Obsidian:** Esta suite de documentación mantiene soporte nativo integral para [Obsidian](https://obsidian.md/). Abra la carpeta del repositorio `CARINA_CORE` como una Bóveda (Vault) de Obsidian para navegar interactivamente a través del grafo técnico de enlaces bidireccionales y notas vinculadas.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
