# 🗄️ Base de Datos y Esquemas Relacionales

Este documento detalla el motor de persistencia relacional asíncrono de CARINA, los esquemas de tablas en PostgreSQL y SQLite, y las credenciales basadas en la metodología 12-Factor App.

⬅️ [Centro de Documentación](../README.md) | 🏛️ [Arquitectura](architecture.md)

---

## 1. Persistencia Asíncrona con Compresión Delta
Las decisiones de IA y telemetría de tráfico se encolan en memoria RAM (< 0.001 ms) y se escriben por lotes (50 registros o 3.0 s). La compresión delta por codificación de longitud de secuencia reduce el consumo en disco en un **97.9%**.

---

## 2. Tablas Principales
- **`step_decisions`:** Registro de acciones sugeridas, vetos de seguridad del Guardian y tiempos de ejecución con enums Smallint de 1 byte.
- **`synapse_fluid_dynamics`:** Registro de telemetría de fluidodinámica de tráfico por carril.
- **`hardware_controller_connections`:** Parámetros de conexión con controladores físicos (IP, puerto, comunidad SNMP).
- **`users`:** Cuentas de operadores y contraseñas hasheadas con bcrypt.
