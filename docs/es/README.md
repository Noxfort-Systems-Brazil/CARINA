<div align="center">

# CARINA — Suite de Documentación Técnica
### Arquitectura de Sistemas, Integración de Hardware y Marco de Seguridad
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Activo-brightgreen?style=flat&logo=github)](https://github.com/Noxfort/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Traducciones / Idiomas:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Centro de Documentación](../README.md)**

---

</div>

## Bienvenido a la Documentación Técnica Oficial

Este directorio contiene la suite completa de documentación técnica en **Español** para **CARINA** (Cognitive Autonomous Real-time Intersection Network Architecture) — un ecosistema empresarial de Aprendizaje por Refuerzo Profundo distribuido para el control semafórico adaptativo en tiempo real.

## Directorio de Guías Técnicas

| Documento | Tema | Contenido Principal |
|---|---|---|
| 📖 **[Arquitectura del Sistema](architecture.md)** | Arquitectura Central | 8 microservicios de SO concurrentes, atención en grafos ST-GATv2 Lite, Agente Consultor PAE (128 canales) y aceleración AMP/TensorCores. |
| 🔌 **[Controladores de Hardware y Gateway Go](hardware_drivers.md)** | Controladores Físicos | Gateway compilado en Go (`carina-go`), IPC sin puertos mediante pipes NDJSON, protocolos NTCIP 1202, UTMC2 y fail-safe atómico. |
| 🛡️ **[Seguridad, Watchdog y FENIX](safety_and_watchdog.md)** | Seguridad Neuro-Simbólica | Reglas de veto simbólico (SR-01 a SR-05), D3QN Guardian contra desbordamiento (spillback), Watchdog en tiempo real (< 500 ms) y auto-resurrección con F.E.N.I.X. |
| ⚡ **[API Synapse HFT y Colas IPC](api_reference.md)** | Interfaz de Alta Frecuencia | Interfaz gRPC de sub-milisegundo Synapse HFT (puerto 50051), 10 canales IPC delimitados y transporte polimórfico de telemetría (MQTT y HTTP/REST). |
| 🗄️ **[Base de Datos y Almacenamiento Delta](database_and_schemas.md)** | Persistencia y Esquemas | Motor de persistencia asíncrono con compresión delta en PostgreSQL (**97.9% de reducción de almacenamiento**), enums Smallint de 1 byte y 12-Factor `.env`. |
| 🧪 **[Pruebas y Control de Calidad](testing.md)** | Aseguramiento de Calidad | Suite de pruebas Pytest con 53 módulos unitarios, pruebas nativas en Go (`go test`), simulación determinista de controladores y cobertura. |
| 🔍 **[IA Explicable (XAI) y SAS](xai_and_sas.md)** | Auditoría Forense Municipal | Google Captum Integrated Gradients, las 5 ecuaciones matemáticas formales y generador de informes periciales Word (.docx) compatibles con normas internacionales. |

---

<div align="center">
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i>
</div>
