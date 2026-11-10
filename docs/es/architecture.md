---
tags: [arquitectura, nucleo, sistema, gatv2, pae, pbt, amp, multiprocesamiento]
aliases: [Arquitectura del Sistema, Esquema de Multiprocesamiento, Visión General del Sistema]
---

# 🏛️ CARINA: Esquema del Sistema y Arquitectura de Multiprocesamiento

Este documento especifica la arquitectura interna de ingeniería del ecosistema CARINA. Detalla los 8 microservicios concurrentes en procesos del sistema operativo, la topología canónica de redes neuronales profundas (LocalAgent PPO-TCN, GuardianAgent D3QN y StrategistAgent ST-GATv2 Lite), el `TopologicalScaler`, los controladores de hardware físico y el motor asíncrono de persistencia con compresión delta en PostgreSQL.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🚨 Ver [Preempción EVP](evp_and_preemption.md) | 🚦 Ver [Controladores de Hardware](hardware_drivers.md) | 🧠 Ver [Formulaciones Neuronales](research_notes.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md)

---

## 1. Modelo de Concurrencia de Microservicios Multiproceso

El Global Interpreter Lock (GIL) de Python impide que la inferencia de IA intensiva en CPU y las operaciones pesadas de E/S se ejecuten en verdadero paralelismo multihilo. Para garantizar una latencia de actuación en sub-milisegundos, CARINA implementa un **modelo de microservicios multiproceso** orquestado por [`carina.py`](../../carina.py) y [`src/launcher/process_manager.py`](../../src/launcher/process_manager.py), combinado con un **Gateway de Hardware y Web en Go** de nivel industrial (`bin/carina-go`):

```mermaid
graph TD
    Launcher[carina.py Orquestador / UI Tray] -->|Inicia y Monitorea| PM[ProcessManager]

    PM --> CC[1. Proceso CentralController]
    PM --> AI[2. Motor AI_Process]
    PM --> WD[3. Proceso Watchdog]
    PM --> SDS[4. DashboardService SDS]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. Motor MFD_Worker]

    CC <-->|IPC Pipe| AI
    CC -->|Cola wd (Heartbeats)| WD
    AI -->|Cola db| DB
    CC -->|Cola sds| SDS
    CC -->|Cola sas| SAS
    CC -->|Cola mfd_trigger| MFD
    MFD -->|Cola mfd_results| CC
    SAS -->|Cola sas_results| CC
    XAI -->|Logs HFT en Disco| AI

    CC <-->|NDJSON Stdin/Stdout| GW[Go Gateway carina-go]
    GW --> NTCIP[Controladores de Campo NTCIP / UTMC UDP 161]
    GW --> WebGW[Go Web Gateway Puerto 2201 / Tailscale]
    WebGW --> CCO[Mapa Web CCO React/TSX src_tsx]
    WebGW <--|POST 204 Telemetría| EVP[Antenas GPS EVP Puerto 8085]
```

---

## 2. Arquitectura de Deep Learning Avanzada

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │   Auto-detecta Nodos del Mapa (N) -> Dim Latente (32/64/128/256), Cabezas (2/4/8/16)│
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │      LOCAL AGENT (PPO)      │           │   STRATEGIST AGENT (GRAFO)  │
     │  Backbone Táctico TCN       │           │   Coordinador ST-GATv2 Lite │
     │  (Actuación Sub-segundo)    │◄──────────┤   (Ondas Verdes Arteriales) │
     └──────────────┬──────────────┘Vec Contexto└──────────────┬──────────────┘
                    │                                         │
                    │ Acción Propuesta                        │ Contexto de Red
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │   Escudo Neuro-Simbólico, Prevención de Spillback y Veto de Tráfico   │
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 Módulo ST-GATv2 Lite (`src/models/st_gatv2_lite.py`)
- **Propósito:** Sincronización espacial de "Ondas Verdes" arteriales a lo largo de intersecciones contiguas en el grafo de la red vial urbana.
- **Ponderación Dinámica:** Mientras que la topología física de las calles es estática, los coeficientes dinámicos de atención espacial $\alpha_{ij}(t)$ se recalculan en tiempo real basándose en las densidades de vehículos entrantes y los gradientes de velocidad.
- **Coordinación Descentralizada:** El Strategist calcula periódicamente el tensor de contexto espacio-temporal a través de la red y lo suministra a los agentes Local y Guardian, permitiendo la emergencia de olas verdes sin necesidad de comandos centralizados como puntos únicos de falla.

### 2.2 Autoencoder Predictivo Universal (`src/models/pae.py`)
- **Propósito:** Motor de representación física compartida de alta capacidad que comprime la dinámica secuencial de pasos múltiples en espacios latentes invariantes ($Z \in \mathbb{R}^{16\dots 128}$).
- **Enriquecimiento Focalizado:** Proporciona representaciones latentes compactas de predicción temporal para potenciar tanto las decisiones de política del LocalAgent como las auditorías de spillback del GuardianAgent.

### 2.3 Auto-Escalador Topológico $O(1)$ (`src/utils/topo_scaler.py`)
- **Escalado Algorítmico:** Detecta automáticamente la densidad de la red ($N$ intersecciones) y ajusta de forma autónoma las dimensiones neuronales en potencias de 2 optimizadas para TensorCores de NVIDIA:
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$ (ej., Malla Metropolitana de Londrina)
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$ (Malla de Megalópolis)

### 2.4 Aceleración Universal AMP y TensorCore
- Todas las pasadas hacia adelante (forward passes) de las redes neuronales están encapsuladas en `torch.amp.autocast`, permitiendo aceleración de hardware nativa en FP16/TF32 a través de los TensorCores de NVIDIA y restringiendo el consumo total de VRAM a solo **~20 MB** para los modelos centrales.

---

## 3. Motor de Persistencia de Datos y Almacenamiento Delta

CARINA implementa un motor de persistencia asíncrono que incorpora **Compresión Delta Run-Length** en PostgreSQL:
- **`step_decisions`**: Almacena sugerencias, vetos de seguridad del Guardian y temporizadores de paso despachados vía [`StepDecisionWorker`](../../src/database/step_decision_worker.py) en colas RAM no bloqueantes (sobrecarga $< 0.001\text{ ms}$).
- **`edge_dictionary`**: Asocia nombres largos de vías con enteros de 4 bytes para una indexación compacta.
- **Reducción de Almacenamiento:** Logra una **reducción del 97.9% en la huella de almacenamiento** (~380 MB/día para una red metropolitana de 200 intersecciones).

Para esquemas de base de datos y detalles de consultas, consulte [Arquitectura de Base de Datos y Esquemas](database_and_schemas.md).

---

## 4. Arquitectura de Configuraciones Modulares (`src/settings/`)

Para adherirse a los principios de **Responsabilidad Única** (Single Responsibility) y **Segregación de Interfaces** (Interface Segregation) de SOLID, la gestión de configuración de CARINA se descompone en componentes desacoplados y testeables:

```text
       ┌────────────────────────────────────────────────────────┐
       │               SettingsService (Orquestador)            │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(Validación y  │     │& Write       │ │(E/S Archivo    │ │(Secretos de Entorno  │
│ Mapa Secciones│     │(Interfaces)  │ │ settings.ini)  │ │ .env App 12-Factores)│
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ Fachada de Compatibilidad Hacia Atrás
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`):** Registro autoritativo que define mapeos de clave a sección, valores por defecto de respaldo y reglas de validación de tipos.
- **`IniFileStorage` (`src/settings/ini_storage.py`):** Gestiona la lectura de archivos y la escritura persistente en `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** Resuelve secretos sensibles de infraestructura desde `.env` utilizando `python-dotenv` con análisis de archivo de respaldo.
- **`SettingsService` (`src/settings/service.py`):** Servicio central que orquesta la obtención, validación y serialización de configuraciones.
- **`SettingsManager` (`src/utils/settings_manager.py`):** Fachada de compatibilidad hacia atrás que garantiza cero regresiones para llamadas heredadas.

---

## 5. Arquitectura Polimórfica de Monitoreo y Transportes (`src/transports/`)

CARINA cuenta con una **capa polimórfica de transporte de telemetría e incidentes** que permite la monitorización remota en tiempo real sobre brokers MQTT locales, webhooks remotos, APIs REST en la nube o soluciones de túnel (ej., Ngrok):

```text
IncidentReporter / TelemetryLoop
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (Fachada Singleton)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (Fábrica con Resolución Automática de Endpoint)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│  (Broker Local / de Red)  │             │ (API REST / Nube / Ngrok) │
│ - Host:Puerto (ej. :1883) │             │ - http:// o https://      │
│ - Telemetría QoS 0/1      │             │ - Sesión HTTP Persistente │
│ - Tópicos: noxfort/telem/ │             │ - Reintento backoff expon.│
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 Abstracción de Transporte (`BaseMonitorTransport`)
Define el contrato estricto para todos los exportadores externos de telemetría:
- `setup()`: Configura endpoints, tiempos de espera (timeouts) y credenciales.
- `ensure_connected()`: Establece o valida la conectividad.
- `publish(topic, payload)`: Transmite cargas útiles JSON de forma asíncrona o en hilos de trabajo dedicados.
- `disconnect()`: Vacía búferes pendientes y finaliza limpiamente las sesiones.

### 5.2 Resolución Automática de Endpoint (`endpoint_resolver.py`)
Clasifica de forma inteligente los endpoints de destino sin requerir configuración explícita de protocolo:
- URLs que comienzan con `http://` o `https://` (o dominios que contengan `ngrok`, `run.app` o `/api/`) instancian `MonitorHttpTransport`.
- Cadenas estándar de nombre de host o IP (`localhost`, `10.0.0.1`, `broker:1883`) instancian `MonitorMqttTransport`.

### 5.3 Deduplicación de Incidentes y Filtrado de Alertas (`src/drivers/`)
- [`IncidentReporter`](../../src/drivers/incident_reporter.py) transmite cambios en el estado de conexión de hardware y errores de controladores a herramientas de monitoreo externo.
- [`IncidentFilter`](../../src/drivers/incident_filter.py) suprime avalanchas de alertas almacenando en caché hashes de incidentes activos con desrebote temporal (timestamp debouncing), manteniendo `.carina_incident_filter_cache.json` a lo largo del ciclo de vida del sistema.

---

## 6. Gateway de Hardware de Campo de Alto Rendimiento (`src_go/`)

Para lograr confiabilidad de nivel industrial, determinismo de red de sub-milisegundo y cero contención del GIL en despliegues en campo, CARINA descarga toda la comunicación con controladores de tráfico reales (puertos UDP 161 y 162) a un **Gateway de Hardware en Go** dedicado y compilado (`bin/carina-go` construido desde `src_go/`):

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │   [Synapse Perception]  <-- gRPC (50051) -->  [Cámara] │
       │            │                                           │
       │      [Motor IA / NN]                                   │
       │            │                                           │
       │     [ActionSupervisor]                                 │
       │            │                                           │
       │ [HardwareConnectionManager] (Orquestador Python)       │
       │            │                                           │
       │    [GoGatewayClient] (Gestor de Subproceso Pipe)       │
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout (JSON Delimitado por Líneas - NDJSON)
                    │ CERO PUERTOS DE RED ABIERTOS EN EL HOST
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │          CARINA HARDWARE GATEWAY (Demonio Go)          │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [Escáner IPC NDJSON y Escritor Concurrente]       │
       │  +-- [Registro de Conexiones HardwareManager]          │
       │  +-- [Fail-Safe Atómico ante EOF / SIGPIPE]            │
       │  +-- [Motor de Latidos: time.Ticker por intersección]  │
       │  +-- [Despachadores de Protocolo NTCIP 1202 y UTMC2]   │
       │  +-- [Pool de Clientes GoSNMP (UDP 161)]               │
       │  +-- [Servidor TrapListener (UDP 162)]                 │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Traps)
                            ▼                  ▼
                    [Controlador Campo]  [Controlador Campo] ...
```

### 6.1 Propiedades Arquitectónicas Clave
- **Cero Puertos Abiertos en el Host:** El enlace de control entre Python y Go se ejecuta exclusivamente sobre tuberías estándar anónimas (búferes en anillo del kernel `pipe(2)`). No se exponen puertos localhost, sockets TCP ni servicios HTTP.
- **Fail-Safe de Seguridad Atómica:** Si el proceso de IA de Python falla o se cierra, el kernel cierra la tubería. El binario en Go detecta `EOF` en `os.Stdin` en microsegundos y dispara de inmediato `EmergencyReleaseControlAll()` vía SNMP, liberando con seguridad las retenciones remotas y devolviendo los controladores a sus planes locales autónomos.
- **Cero Contención de GIL:** Las goroutines gestionan el sondeo concurrente, los latidos keepalive de 2.0s y la recepción de traps UDP 162 independientemente de las pesadas operaciones de tensores PyTorch en Python.
- **Adaptador Transparente (`GoTrafficDriverProxy`):** Cumple con el Principio de Sustitución de Liskov (LSP) implementando `BaseTrafficDriver`, haciendo que el gateway en Go sea 100% transparente para el resto de la base de código de CARINA.

---

## 7. Supervisor de Procesos y Subsistema de Recuperación ante Fallos F.E.N.I.X. (`src/fenix/`)

CARINA incorpora **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) para garantizar auto-recuperación continua autónoma 24/7 para el motor de inferencia de IA:

```text
       ┌────────────────────────────────────────────────────────┐
       │              Monitor de Salud Watchdog                 │
       └───────────────────────────┬────────────────────────────┘
                                   │ Timeout / Latido Perdido
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            FenixSupervisor (Orquestador)               │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- Backoff de ventana móvil  │ │- Ciclo vida subproceso  │
       │- Limitador cuota reinicios │ │- SIGTERM / SIGKILL      │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ Resurrección
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- Telemetría FROZEN_SYNC │
                                      │- Handshake en Límites   │
                                      │- Traspaso sin colisión  │
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`):** Coordina la terminación de subprocesos, el retroceso (backoff) de recuperación, la resurrección del proceso hijo y la reconciliación del estado.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** Calcula los retrocesos exponenciales y aplica límites de tasa de reinicio para evitar tormentas de reinicios en cascada.
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** Gestión de subprocesos de bajo nivel garantizando aislamiento determinista de procesos y terminación limpia mediante SIGTERM/SIGKILL.
- **`StateReconciler` (`src/fenix/state_reconciler.py`):** Asegura que el motor de IA resucitado opere en modo `FROZEN_SYNC` y solo asuma el control de actuación en límites de fase limpios cuando los controladores físicos transicionen de etapa de manera natural.

---

## 8. Ciclo de Vida del Agente, PBT Intra-Fase y Motor de Promoción (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA estructura las políticas de aprendizaje por refuerzo como un organismo en evolución sometido a un currículo de desarrollo de 3 etapas:

```text
  ┌──────────────────┐      Caída de Entropía y Ritmo     ┌──────────────────┐    Entropía y Margen Fluido (delta*)    ┌──────────────────┐
  │   ETAPA CHILD    │ ─────────────────────────────────> │    ETAPA TEEN    │ ───────────────────────────────────────>│   ETAPA ADULT    │
  │  (Modo Shadow)   │                                    │(Autonomía Off-Pk)│                                         │(Autonomía Total) │
  └────────┬─────────┘                                    └────────┬─────────┘                                         └────────┬─────────┘
           │                                                       │                                                            │
           ▼                                                       ▼                                                            ▼
  [Protegido de PBT]                                      [PBT Intra-Fase]                                              [PBT Intra-Fase]
  [Observa Dinámica Fluidos]                              (Solo TEEN <-> TEEN)                                          (Solo ADULT <-> ADULT)
  [Piso Mínimo 1 Semana]                                  [Modo Sombra en Picos]                                        [Control Activo 24/7]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`):** Servicio de Aplicación Central y Fachada que orquesta las evaluaciones de madurez de agentes, respaldado por la entidad `AgentMaturity`, `MaturityConfig` y `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`):** Ejecuta **Entrenamiento Basado en Población (PBT) Intra-Fase**. Los agentes se clonan y mutan estrictamente dentro de su cohorte de pares (`TEEN` con `TEEN`, `ADULT` con `ADULT`), mientras que los agentes `CHILD` permanecen completamente protegidos. Incluye verificación de dimensiones de tensores para evitar caídas entre intersecciones heterogéneas.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`):** Comprueba rigurosamente la entropía de política de Shannon, las duraciones mínimas de episodios y las metas de rendimiento.
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`):** Dimensiona dinámicamente los pasos por episodio a partir de la topología física (unificando vías bidireccionales, descartando conectores internos `:` y aplicando relajación sub-lineal $\sqrt{N}$ y $D_{\text{km}}$), calculando el piso inviolable de 1 semana completa ($E_{\text{semana}}$ episodios a $\Delta t = 250\text{ ms}$).
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`):** Rastrea y persiste atómicamente la cobertura de las 168 horas semanales ($7\text{ días} \times 24\text{ horas}$), asegurando resiliencia ante pausas y reinicios del proceso sin perder el historial de maduración.
- **`ActionAuthorizer` (`src/core/action_authorizer.py`):** Restringe el control físico del agente `TEEN`, forzando modo sombra en horarios punta urbanos clásicos (06:30-09:00 y 17:00-19:30 en días laborables) o según la programación de Synapse.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`):** Orquesta el ritmo dinámico integrando `EpisodeStepCalculator` y haciendo cumplir el piso inviolable de seguridad ($t_{\min} = \max(E_{\text{semana}}, \text{configuracion})$).
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`):** Calcula continuamente los márgenes de graduación requeridos $\delta^* \in [3.0\%, 25.0\%]$ utilizando telemetría empírica de velocidad y ocupación infantil desde `synapse_fluid_dynamics`.

---

## 9. Subsistema de Balance Físico de Recompensas (`src/engine/reward_weights_calculator.py`)

Para eliminar la distorsión del gradiente donde los tiempos de espera acumulados eclipsan el flujo de vehículos por órdenes de magnitud, CARINA equilibra la ecuación de recompensa según la física de recorrido de enlaces del Highway Capacity Manual (HCM):

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`):** Calcula pesos de recompensa normalizados al cargar la topología de la red (`TopologyManager.load_topology`).
- **`RewardCalculator` (`src/engine/reward_calculator.py`):** Ingiere pesos dinámicos mediante `set_reward_weights`, estableciendo un equilibrio donde los incentivos de descarga de vehículos igualan la escala del retraso acumulado en cola.

---

## 10. Subsistema de Horarios de Destello Amarillo Nocturno (`src/controller/yellow_schedule_manager.py`)

Para la seguridad vial y el cumplimiento normativo durante las horas nocturnas de bajo volumen, CARINA integra un subsistema autónomo de programación de destello amarillo:
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`):** Evalúa ventanas de tiempo programadas (ej., 23:00 a 05:00) contra la hora actual del sistema, comandando de forma autónoma los controladores físicos a modo de destello amarillo o transicionando de regreso al control adaptativo por IA en los límites de la ventana.
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`):** Interfaz de usuario que permite a los operadores habilitar/deshabilitar horarios, personalizar rangos de tiempo y asignar selectivamente intersecciones individuales o redes metropolitanas completas.

---

## 11. Subsistema de Preempción de Vehículos de Emergencia (EVP) (`src/evp/`, `src_go/evp_go/`)

Para otorgar Corredores Verdes instantáneos a vehículos de respuesta ante emergencias (ambulancias SAMU, Bomberos, Policía) en cumplimiento con la Resolución CONTRAN nº 960 y normativas de tránsito internacional (CTB Art. 29 / MUTCD), CARINA incorpora un subsistema dedicado de Preempción de Vehículos de Emergencia:

```text
 Antena GPS / Baliza       Gateway Web Go (:2201 / :8085)         EVPService (src/evp/)
          │                             │                                   │
          │── POST /api/v1/evp/telemetry─>│                                 │
          │   (HTTP 204 No Content)     │── NDJSON / Stream en Memoria ────>│
          │                             │                                   ├── Cinemática (Haversine WGS84)
          │                             │                                   ├── Entrada Bloque (60m <= d <= 160m)
          │                             │                                   └── Verificación de Sirena Activa
          │                             │                                           │
          │                             │                                           ▼
          │                             │                                 SafetyAuditor (Regla #0)
          │                             │                                 (Despeje -> ACTION_HOLD)
          │                             │                                           │
          │<───── Corredor Verde ───────┼── SNMP ascPhaseHold (Despachador Go) <────┘
```

- **Disparador de Doble Factor:** La preempción requiere simultáneamente la entrada al bloque de aproximación ($60\text{ m} \le d \le 160\text{ m}$) Y sirena acústica/óptica activa (`siren_active = True`).
- **Interceptación Prioritaria en SafetyAuditor:** La Regla #0 intercepta las acciones propuestas, respeta los intervalos de despeje (amarillo y todo-rojo) y mantiene la retención de verde (`ACTION_HOLD = 1`).
- **Límite de Watchdog Regulatorio ($45\text{ s}$):** Aborta las retenciones incondicionalmente tras 45 segundos para prevenir bloqueos viales en arterias cruzadas.
- **Liberación Inmediata (Checkout):** Tan pronto como el vehículo cruza la línea de detención ($d \le 15\text{ m}$), la preempción se libera inmediatamente.

Para especificaciones técnicas completas, consulte [Preempción de Vehículos de Emergencia (EVP)](evp_and_preemption.md).

---

## 12. Arquitectura Web del Operador del Centro de Control (CCO) (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA proporciona un centro de operaciones basado en web para videowalls municipales y monitoreo remoto:
- **`WebGatewayServer` (`src_go/web_gateway/server.go`):** Servidor HTTP embebido en Go ejecutándose en el puerto 2201 (o puerto configurado) que proporciona streaming de eventos SSE (`/cco/stream`), endpoints de topología (`/cco/topology`) y tunelización remota cifrada con Tailscale Funnel.
- **`CCO Web Application` (`src_tsx/src_cco/`):** Aplicación moderna construida con React 18, TypeScript, Tailwind CSS, renderizador de capas de mapa en SVG y panel de control Apache ECharts que muestra en tiempo real posiciones de vehículos, temporización semafórica y notificaciones emergentes de alerta de preempción.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
