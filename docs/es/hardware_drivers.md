---
tags: [hardware, controladores, ntcip, utmc, snmp, failsafe]
aliases: [Controladores de Hardware, Controladores Físicos, NTCIP 1202, Integración UTMC]
---

# 🚦 Controladores de Hardware e Integración de Controladores Físicos

Este documento especifica la capa de integración de hardware físico de CARINA ubicada en [`src/drivers/`](../../src/drivers) y [`src/controller/`](../../src/controller). Detalla los protocolos de comunicación (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), la gestión del ciclo de vida de las conexiones, la adquisición de telemetría de hardware y la transferencia determinista a modo fail-safe.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🏛️ Ver [Arquitectura de Multiprocesamiento](architecture.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Visión General Arquitectónica

CARINA se conecta con controladores de tráfico semafórico del mundo real (ej., Econolite, Siemens, Peek, SWARCO, Yunex) mediante un **Gateway de Hardware en Go** de alto rendimiento (`bin/carina-go` compilado desde [`src_go/`](../../src_go)). La comunicación entre el núcleo de Python de CARINA y el Gateway en Go se ejecuta estrictamente a través de **tuberías estándar del sistema operativo (`stdin`/`stdout`)** utilizando JSON Delimitado por Líneas (NDJSON). Esto garantiza **cero puertos locales IPC abiertos en la máquina host**, ejecución en sub-milisegundos y liberación absoluta de la sobrecarga del GIL de Python.

### 1.1 Propiedad Única del Gateway (`CARINA_GATEWAY_ROLE`) y Arquitectura en Lazo Cerrado
Para prevenir procesos `bin/carina-go` duplicados, colisiones en el puerto UDP `162` del receptor de traps y estado SNMP dividido (*split-brain*):
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`):** Inicia en exclusiva `bin/carina-go`, aloja [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (compuesto por `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher` y `TailscaleGatewayAdapter`), posee las conexiones SNMP locales de `HardwareConnectionManager` y difunde instantáneas a los workers subordinados.
- **`AI_Process`, `SDS` y `UI` (`CARINA_GATEWAY_ROLE=remote`):** Operan como espejos remotos sin lanzar binarios Go locales ni enlazar el puerto UDP `162`. [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py) (materializado por [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py)) reenvía acciones (`ai_hardware_cmd`) y preempciones EVP (`ai_evp_preempt`) de regreso a `CentralController` sobre [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Decodificación de Telemetría en Lazo Cerrado:** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) y [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) traducen las máscaras de bits reales de los controladores (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) de vuelta a índices de etapa SUMO base 0 para la extracción de estado de la IA y la reconciliación de traspaso F.E.N.I.X.

Además del control estándar NTCIP/UTMC, el gateway en Go incluye un **Despachador de Preempción EVP** (`src_go/evp_go/dispatcher.go`) para la aserción de retenciones de fase en microsegundos y un **Gateway Web Remoto** (`src_go/web_gateway/server.go`) que proporciona conectividad en malla Tailscale autenticada por token, terminación TLS, ingestión telemétrica HTTP (puerto `2201`) y streaming por Server-Sent Events (SSE) para videowalls de CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │     CentralController (CARINA_GATEWAY_ROLE=owner)      │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │ (Estado y SNMPv2/v3) │   │   │ (Watchdog de Latido) │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │(Despacho Preempción) │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │(Subproceso Pipe Python) │
                     └────────────┬────────────┘
                                  │ stdin / stdout (IPC NDJSON - Cero Puertos Control Local)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │            CARINA HARDWARE GATEWAY (Binario Go)           │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │ Controlad. NTCIP   │         │ Controlador UTMC   │   │
      │   │ (NTCIP 1202 v02)   │         │(Estándar UK UTMC2) │   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │  Despachador EVP │ │GoSNMPv2/3│ │Decod.Traps Binar.│   │
      │  │(Hold OID Directo)│ │Pto UDP161│ │(SNMPv1/v2c/v3)   │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestión Web Remota y Malla
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │      Gateway Web y Malla Tailscale (Puerto 2201 / TLS)    │
      │  - Fail-closed por defecto (HTTP 503 al estar deshabilit.)│
      │  - POST /api/v1/evp/telemetry (Token Auth, HTTP 204)      │
      │  - GET /cco/stream (Token Auth, CORS, Videowall SSE)      │
      │  - Tailscale Funnel / Redes Superpuestas Seguras Peer     │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. Controlador de Semáforo Actuado NTCIP 1202 (ASC)

El **estándar NTCIP 1202** (National Transportation Communications for ITS Protocol) es la norma predominante en Norteamérica y en implementaciones modernas de ITS en todo el mundo.

### 2.1 Arquitectura de Archivos
**Implementación del Gateway en Go (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go): Orquestador nativo del controlador NTCIP en Go.
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go): Sondeador telemétrico de fase activa, estado de anillos y actuaciones de detectores.
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go): Motor de inyección de retención de fase (hold), corte forzado (force-off) y llamadas de demanda (call).
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go): Traduce las acciones discretas de CARINA en máscaras de bits de fases NTCIP.
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) y [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json): Definiciones embebidas de perfiles OID.

**Capa de Puente y Proxy en Python (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py): Cliente IPC de tubería anónima NDJSON que administra el subproceso `bin/carina-go`.
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py): Proxy directo `BaseTrafficDriver` que reenvía comandos al demonio en Go.
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py): Instancia proxies de controladores basados en autodetección de marca/modelo.

### 2.2 Tabla de Mapeo de OIDs Estándar (`src_go/configs/ntcip_oids.json`)

Todos los OIDs de estado (`phaseStatusGroup`) y control (`phaseControlGroup`) de NTCIP 1202 admiten PDUs tanto de tipo entero como `OCTET STRING`/`BitString` mediante [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go), y pueden anularse por intersección mediante `config_path`:

| Clave del Objeto | OID ASN.1 | Grupo / Tipo | Descripción |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | Estado / Máscara | Máscara de bits de fases actualmente en indicación Roja. |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | Estado / Máscara | Máscara de bits de fases actualmente en indicación Amarilla. |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | Estado / Máscara | Máscara de bits de fases actualmente en indicación Verde. |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | Estado / Máscara | Llamadas activas de detección vehicular reportadas por el controlador. |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | Estado / Máscara | Llamadas activas de pulsadores peatonales reportadas por el controlador. |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | Control / Máscara | Omite fases específicas del servicio. |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | Control / Máscara | Mantiene en verde la fase activa (`ascPhaseControlHold`). |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | Control / Máscara | Fuerza la terminación de la fase verde actual (`ascPhaseControlForceOff`). |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | Control / Máscara | Inyecta llamada sintética de detección vehicular (`ascPhaseControlVehCall`). |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | Control / Máscara | Inyecta llamada peatonal sintética (`ascPhaseControlPedCall`). |

---

## 3. Controlador UTMC / UTMC2 y Soporte SNMPv3 USM

Para intersecciones que utilizan el marco británico **Urban Traffic Management and Control (UTMC)** o gabinetes de campo autenticados con **SNMPv3**:

### 3.1 Arquitectura de Archivos
**Implementación del Gateway en Go (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Manejador nativo de comunicación UTMC en Go con `Probe()` y `CloseTransport()` seguros para hilos.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Analizador de confirmación de etapas (`status_active`, `status_leaving`, `status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`, `status_ped_demand`).
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Ejecución de demanda de etapa, retención, corte forzado y acciones lógicas seguras respecto al entreverde (*intergreen*).
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Asocia etapas UTMC (Etapas 1..8) con acciones neuronales de CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) y [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Definiciones embebidas de perfiles OID para UTMC.
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go): **Motor SNMPv3 USM** compatible con `NoAuthNoPriv`, `AuthNoPriv` y `AuthPriv`, con protocolos de autenticación (`MD5`, `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512`) y cifrado de privacidad (`DES`, `AES`, `AES192`, `AES256`, `AES192C`, `AES256C`). Los metadatos JSON `snmp_config` y las anulaciones de OID `config_path` por intersección se propagan desde [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) y [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) a través de [`DriverFactory`](../../src/drivers/driver_factory.py) hacia `GoGatewayClient`.

---

## 4. Despachador de Preempción de Hardware EVP (`src_go/evp_go/`)

El **Despachador de Preempción EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) gestiona solicitudes de corredores verdes de emergencia en tiempo real con actuación en microsegundos sobre controladores físicos:

- **Bypasa el Ciclo de Inferencia:** Los disparadores de preempción se saltan la selección de acciones por la red neuronal y los ciclos de coordinación inter-intersección, aplicando directamente retenciones verdes en las fases semafóricas de destino.
- **Inserción Directa de Hold OID por SNMP:** Convierte índices de etapas de verde (`stage_idx` y `stage_codes`) a máscaras de bits de `phase_control.hold` (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) de NTCIP o retenciones de etapa UTMC, manteniendo en rojo el tráfico en conflicto mientras otorga derecho de paso continuo e ininterrumpido.
- **Protocolo IPC en Microsegundos:** Se activa mediante el comando NDJSON `evp_preempt` sobre las tuberías del sistema operativo:
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **Watchdog de Failsafe y Liberación de Retención:** Las retenciones se cancelan cuando el vehículo cruza el umbral de salida ($\le 15\text{ m}$) o al expirar el temporizador de permanencia máxima del watchdog ($45\text{ s}$). Si el gateway se cae o se desconecta, los controladores físicos liberan automáticamente las retenciones tras perder 3 latidos consecutivos.

---

## 5. Gateway Web Remoto y Red en Malla (`src_go/web_gateway/`)

Para arquitecturas distribuidas de ciudades inteligentes donde vehículos de emergencia u operadores centrales requieren conectividad remota sin exponer direcciones IP públicas:

- **Malla Cifrada Tailscale:** Integrada vía [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go), permitiendo a los controladores en el borde de CARINA formar redes superpuestas seguras de confianza cero con cifrado de extremo a extremo.
- **Tailscale Funnel (Puerto 2201):** Expone públicamente endpoints de ingestión de alto rendimiento sobre TLS sin abrir puertos locales en firewalls ni configurar reenvío de puertos.
- **Receptor Telemétrico de Alta Capacidad:** Expone `POST /api/v1/evp/telemetry` (HTTP 204 fire-and-forget) para ingerir balizas GPS vehiculares de alta frecuencia con latencia de respuesta sub-milisegundo.
- **Hub de Difusión Server-Sent Events (SSE):** [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) transmite telemetría de intersecciones en tiempo real, rastreo de vehículos de emergencia y estados semafóricos a los videowalls del Centro de Control Operativo (CCO) mediante `GET /cco/stream`.

---

## 6. Gestión de Hardware y Arquitectura Fail-Safe

### 6.1 Ciclo de Vida de Conexiones y Pooling (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) y [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py): Administran las máquinas de estados de conexión (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`), vistas espejo pasivas en modo `remote` (`update_remote_hardware_status`), autodetección de puertos de simulador ([`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)) y restauración masiva desde CSV ([`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)).
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) y [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py): Persisten endpoints IP y JSON opcional `snmp_config` (SNMPv3 USM / `config_path` de OIDs personalizados) en `hardware_controller_connections` y plantillas CSV, preservando [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) como fachada retrocompatible.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Ejecuta la reversión de emergencia mediante `HardwareGatewayCoordinator.on_failsafe_triggered()` y la recuperación mediante `on_failsafe_recovered()`.

### 6.2 Determinismo de Fail-Safe, Recuperación y Traps SNMP Binarios
1. **Pérdida de Latido y Fail-Safe Reversible:** Si se pierde la comunicación con un controlador activo o se dispara el fail-safe del Watchdog, `EmergencyReleaseControlAll()` pausa los latidos y libera las retenciones de fase manteniendo vivos los drivers SNMP y el receptor de traps para que `resume_control` (`ResumeControlAll()`) pueda reanudar sin interrupciones al recuperarse. Al cerrar el proceso o ante `EOF`/`SIGPIPE`, `ShutdownAll()` libera permanentemente las retenciones y cierra los sockets.
2. **Protección de Entreverde (`HardwareStageActuator`):** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) omite llamadas `send_stage_hold` conflictivas durante intervalos de entreverde de amarillo/todo-rojo (`_is_intergreen_stage`) y resuelve uniformemente los IDs con prefijo `tl_`.
3. **Decodificador Binario de Traps SNMPv1/v2c/v3 (`src_go/pkg/traplistener/snmp_decoder.go`):** Analiza paquetes binarios ASN.1 BER Trap/Inform en el puerto UDP `162` (`CARINA_TRAP_PORT`), clasificando alarmas `coldStart`, `warmStart`, `linkDown`, `linkUp`, `authenticationFailure`, NTCIP (`.1206.*`) y UTMC (`.13267.*`, `.2825.*`) por severidad (`CRITICAL`, `WARNING`, `INFO`).
4. **Interceptación de Conflictos de Seguridad:** Todas las acciones salientes atraviesan [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) antes de su despacho, verificando las matrices de conflicto y los despejes reglamentarios entre verdes (*intergreen*).

### 6.3 Notificación de Incidentes de Hardware y Deduplicación (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py): Intercepta cambios en el estado de hardware de los controladores (`CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`) y construye mensajes estandarizados de incidentes en JSON.
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py): Previene avalanchas de notificaciones almacenando en caché hashes de incidentes activos con desrebote temporal en `.carina_incident_filter_cache.json`.
- Despacha alertas dinámicamente vía `MonitorClient` hacia el transporte telemétrico configurado (broker MQTT local o endpoint HTTP/Ngrok remoto).

---

## 7. Seguridad y Credenciales de Red

Las credenciales de hardware nunca deben escribirse directamente en el código. CARINA resuelve los secretos SNMP y de controladores a través de variables de entorno definidas en [`.env`](../../.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

Para configuraciones de seguridad y roles de usuario, consulte [Seguridad y Autenticación](security_and_auth.md).
Para esquemas de serialización telemétrica, consulte [Referencia de API](api_reference.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
