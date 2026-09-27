# ⚡ Referencia de API, Protocolo Synapse HFT y Colas IPC

Este documento especifica la interfaz de comunicación gRPC de alta frecuencia **Synapse HFT** y los canales de comunicación entre procesos (IPC) de CARINA.

⬅️ [Centro de Documentación](../README.md) | 🏛️ [Arquitectura](architecture.md) | 🚦 [Controladores](hardware_drivers.md)

---

## 1. Servicio Synapse HFT (`proto/synapse_hft.proto`)
- **Puerto:** `50051` (TCP / HTTP2).
- **Métodos RPC:**
  - `Ping`: Verificación de disponibilidad con latencia $< 1\text{ ms}$.
  - `LoadScenario`: Carga la geometría y red vial de simulación/campo.
  - `SystemControl`: Comandos de control (`START`, `PAUSE`, `STOP`, `RESET`).
  - `StreamTraffic`: Transmisión en tiempo real de ocupación de vías, velocidades y colas.

---

## 2. Canales IPC Multiproceso
El sistema gestiona 10 canales IPC en memoria (`controller_conn`, `ai_conn`, `wd`, `sds`, `sas`, `ui`, `ui_telemetry`, `db`, `g_state`, `g_signal`) que aíslan las tareas pesadas de inferencia de la interfaz de usuario y las bases de datos.

---

## 3. Telemetría Externa Polimórfica (`src/transports/`)
Soporte dual automático para publicación hacia brokers MQTT locales o endpoints remotos REST/HTTP (Cloud, túneles Ngrok).
