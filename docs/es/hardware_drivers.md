---
tags: [hardware, controladores, ntcip, utmc, snmp, failsafe]
aliases: [Controladores de Hardware, Controladores Físicos, NTCIP 1202, Integración UTMC]
---

# 🚦 Controladores de Hardware e Integración de Controladores Físicos

Este documento especifica la capa de integración de hardware físico de CARINA ubicada en [`src/drivers/`](../../src/drivers) y [`src/controller/`](../../src/controller). Detalla los protocolos de comunicación (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), la gestión del ciclo de vida de las conexiones, la adquisición de telemetría de hardware y la transferencia determinista a modo fail-safe.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🏛️ Ver [Arquitectura de Multiprocesamiento](architecture.md) | 🛡️ Ver [Seguridad y Watchdog](safety_and_watchdog.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Visión General Arquitectónica

CARINA se conecta con controladores de tráfico semafórico del mundo real (ej., Econolite, Siemens, Peek, SWARCO, Yunex) mediante un **Gateway de Hardware en Go** de alto rendimiento (`bin/carina-go` compilado desde [`src_go/`](../../src_go)). La comunicación entre el núcleo de Python de CARINA y el Gateway en Go se ejecuta estrictamente a través de **tuberías estándar del sistema operativo (`stdin`/`stdout`)** utilizando JSON Delimitado por Líneas (NDJSON). Esto garantiza **cero puertos de red abiertos en la máquina host** para la IPC local, ejecución en sub-milisegundos y liberación absoluta de la sobrecarga del GIL de Python.

Además del control estándar NTCIP/UTMC, el gateway en Go incluye un **Despachador de Preempción EVP** (`src_go/evp_go/dispatcher.go`) para la aserción de retenciones de fase en microsegundos y un **Gateway Web Remoto** independiente (`src_go/web_gateway/server.go`) que proporciona conectividad en malla Tailscale, ingestión telemétrica HTTP (puerto `2201`) y streaming por Server-Sent Events (SSE) para videowalls de CCO.

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │ (Estado y Pooling)   │   │   │ (Watchdog de Latido) │
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
                                  │ stdin / stdout (IPC NDJSON - Cero Puertos Host)
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
      │  │  Despachador EVP │ │  GoSNMP  │ │ TrapListener UDP │   │
      │  │(Hold OID Directo)│ │Pto UDP161│ │   (Puerto 162)   │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Ingestión Web Remota y Malla
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │        Gateway Web y Malla Tailscale (Puerto 2201)        │
      │  - POST /api/v1/evp/telemetry (Ingestión GPS HTTP 204)    │
      │  - GET /cco/stream (Hub SSE en Vivo para Videowall)       │
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

### 2.2 Tabla de Mapeo de OIDs Estándar

| Nombre del Objeto | OID ASN.1 | Tipo | Descripción |
| :--- | :--- | :---: | :--- |
| `ascPhaseStatusGroupReds` | `1.3.6.1.4.1.1206.4.2.1.1.1` | `OCTET STRING` | Máscara de bits de fases actualmente en indicación Roja. |
| `ascPhaseStatusGroupYellows` | `1.3.6.1.4.1.1206.4.2.1.1.2` | `OCTET STRING` | Máscara de bits de fases actualmente en indicación Amarilla. |
| `ascPhaseStatusGroupGreens` | `1.3.6.1.4.1.1206.4.2.1.1.3` | `OCTET STRING` | Máscara de bits de fases actualmente en indicación Verde. |
| `ascPhaseHold` | `1.3.6.1.4.1.1206.4.2.1.1.5` | `OCTET STRING` | Mantiene el verde de la fase activa (evita el cambio de fase). |
| `ascPhaseForceOff` | `1.3.6.1.4.1.1206.4.2.1.1.6` | `OCTET STRING` | Fuerza la terminación de la fase verde actual. |
| `ascPhaseCall` | `1.3.6.1.4.1.1206.4.2.1.1.7` | `OCTET STRING` | Inyecta una llamada de detección vehicular sintética para solicitar la fase. |

---

## 3. Controlador UTMC / UTMC2 (Estándar del Reino Unido)

Para intersecciones que utilizan el marco británico **Urban Traffic Management and Control (UTMC)**:

### 3.1 Arquitectura de Archivos
**Implementación del Gateway en Go (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Manejador nativo de comunicación UTMC en Go.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Analizador de confirmación de etapas y tramas de respuesta.
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Ejecución de demanda de etapa y cambio de etapa.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Asocia etapas UTMC (Etapas 1..8) con acciones neuronales de CARINA.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) y [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Definiciones embebidas de perfiles OID para UTMC.

---

## 4. Despachador de Preempción de Hardware EVP (`src_go/evp_go/`)

El **Despachador de Preempción EVP** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) gestiona solicitudes de corredores verdes de emergencia en tiempo real con actuación en microsegundos sobre controladores físicos:

- **Bypasa el Ciclo de Inferencia:** Los disparadores de preempción se saltan la selección de acciones por la red neuronal y los ciclos de coordinación inter-intersección, aplicando directamente retenciones verdes en las fases semafóricas de destino.
- **Inserción Directa de Hold OID por SNMP:** Convierte índices de etapas de verde a máscaras de bits de `ascPhaseHold` (`1.3.6.1.4.1.1206.4.2.1.1.5`) de NTCIP, reteniendo en rojo el tráfico en conflicto mientras otorga derecho de paso continuo e ininterrumpido.
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

### 6.1 Ciclo de Vida de Conexiones y Pooling (`src/controller/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py): Administra las máquinas de estados de conexión (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`).
- [`src/controller/connection_config_repo.py`](../../src/controller/connection_config_repo.py): Persiste direcciones IP, puertos, protocolos y credenciales en la tabla `hardware_controller_connections`.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Ejecuta la reversión de emergencia.

### 6.2 Determinismo de Fail-Safe
1. **Pérdida de Latido (< 500 ms):** Si la comunicación con un controlador activo se interrumpe durante más de 3 intervalos de sondeo consecutivos, CARINA libera todos los comandos de Retención de Fase (Phase Holds) y Corte Forzado (Force-Off).
2. **Reversión al Controlador Local:** El controlador físico revierte inmediatamente a su plan interno local coordinado de tiempo fijo (Hora del Día / Modo Destello), garantizando la seguridad ininterrumpida de la intersección.
3. **Interceptación de Conflictos de Seguridad:** Todas las acciones salientes atraviesan [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) antes de su despacho, verificando las matrices de conflicto y los despejes reglamentarios entre verdes (*intergreen*).

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
