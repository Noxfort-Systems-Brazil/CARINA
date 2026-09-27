# 🚦 Controladores de Hardware y Gateway en Go

Este documento especifica la capa de integración física con controladores de semáforos del sistema CARINA. Detalla la arquitectura del **Gateway Go compilado** (`bin/carina-go`), la comunicación mediante pipes NDJSON, los estándares **NTCIP 1202** y **UTMC / UTMC2**, y los mecanismos de fail-safe determinista.

⬅️ [Centro de Documentación](../README.md) | 🏛️ [Arquitectura](architecture.md) | 🛡️ [Seguridad y Watchdog](safety_and_watchdog.md)

---

## 1. Arquitectura del Gateway de Hardware en Go

Para garantizar determinismo sub-milisegundo y evitar la contención del GIL de Python, todo el tráfico UDP con los controladores de campo (puertos 161 y 162) se gestiona a través del binario nativo compilado **`bin/carina-go`** (`src_go/`):
- **Cero Puertos Host Abiertos:** El enlace de control corre exclusivamente por pipes estándar del SO (`stdin`/`stdout`).
- **Fail-Safe Atómico:** Al cerrarse el pipe por caída del proceso Python, el binario Go detecta el `EOF` en microsegundos y libera el control remoto vía SNMP, regresando los controladores a sus planes locales fijos.

---

## 2. Protocolos Soportados

### 2.1 NTCIP 1202 Actuated Signal Controller (ASC)
Implementado en `src_go/pkg/ntcip/` con perfiles OID dinámicos en `src_go/configs/ntcip_oids.json`. Permite retención de fase (`ascPhaseHold`), terminación forzada (`ascPhaseForceOff`) y llamadas sintéticas de detectores.

### 2.2 UTMC / UTMC2 (Estándar Británico)
Implementado en `src_go/pkg/utmc/` con esquemas en `src_go/configs/utmc_oids.json`. Traduce las fases y demandas de etapa (Stage 1..8) hacia las acciones de IA del CARINA.

---

## 3. Adaptador Python y Reporte de Incidentes (`src/drivers/`)
- `GoGatewayClient`: Administra el ciclo de vida del subproceso Go y la lectura concurrente de respuestas.
- `GoTrafficDriverProxy`: Proxy transparente que implementa `BaseTrafficDriver` (Principio de Sustitución de Liskov).
- `IncidentReporter` & `IncidentFilter`: Publicación de fallas y desconexiones con debounce y caché de estado en `.carina_incident_filter_cache.json`.
