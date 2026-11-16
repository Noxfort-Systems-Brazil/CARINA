<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — Suite de Documentación Técnica
### Arquitectura del Sistema, Integración de Hardware y Marco de Seguridad
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Activo-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Traducciones:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Centro de Documentación](../index.md)**

---

</div>

## Bienvenido a la Documentación Técnica Oficial

Este directorio contiene la suite canónica de documentación técnica en **Español** para **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — un ecosistema empresarial de aprendizaje por refuerzo profundo diseñado para el control semafórico urbano distribuido.

## Directorio de Guías Técnicas

| Documento | Tema | Contenido Principal |
|---|---|---|
| 📚 **[Mapa Central Maestro (MOC)](carina_moc.md)** | Índice Maestro y Grafo de Conocimiento | Visión general del código, jerarquía arquitectónica de directorios y grafo bidireccional Obsidian. |
| 📖 **[Arquitectura del Sistema](architecture.md)** | Arquitectura Central | 8 microservicios concurrentes del SO, propietario único `CARINA_GATEWAY_ROLE`, ST-GATv2 Lite, iTransformer PAE y QR-D3QN. |
| 🚑 **[Preempción de Emergencia (EVP)](evp_and_preemption.md)** | Preempción de Vehículos de Emergencia | Corredores verdes autónomos, cinemática Haversine ($60\text{--}160\text{ m}$), sincronización interproceso y Web Gateway con token (puerto 2201). |
| 🔌 **[Controladores de Hardware y Gateway Go](hardware_drivers.md)** | Controladores de Campo | Gateway Go de propietario único (`carina-go`), IPC por tuberías NDJSON, NTCIP 1202 (`.4.1.*`/`.5.1.*`), UTMC2, SNMPv3 USM, decodificación de etapas en lazo cerrado y traps binarios. |
| 🛡️ **[Arquitectura de Seguridad, Watchdog y FENIX](safety_and_watchdog.md)** | Seguridad Neuro-Simbólica | `PhysicalActionMasker`, reglas simbólicas (SR-00 a SR-06), calibración QR-D3QN + Noisy-OR en `CHILD`, Watchdog y traspaso en lazo cerrado F.E.N.I.X. |
| ⚡ **[API Synapse HFT y Colas IPC](api_reference.md)** | Interfaz de Alta Frecuencia | gRPC Synapse HFT (TLS/mTLS y autenticación Bearer, puerto 50051), 12 colas IPC acotadas + 1 tubería segura para hilos (*thread-safe*) y difusión CCO fijada (*pinned*). |
| 🗄️ **[Arquitectura de Base de Datos y Esquemas](database_and_schemas.md)** | Persistencia y Esquemas | Almacenamiento delta en PostgreSQL (**97.9% de reducción**), `PostgresConnectionPool`, SQLite WAL, SQL `make_interval` y retención EVP de 168h. |
| 🧠 **[Investigación Neuronal y Formulaciones](research_notes.md)** | Modelado Matemático | TCN unificado (`GroupNorm` + `SiLU`), procesamiento por lotes `torch.vmap`, iTransformer PAE, QR-D3QN + Noisy-OR, ST-GATv2 CTDE y DA SILVA binario ($\ln 2$). |
| 🚦 **[Criterios de Ingeniería de Tráfico (MUTCD)](traffic_engineering_warrants.md)** | Ingeniería de Tráfico | Evaluación algorítmica de justificaciones semafóricas regulatorias formales FHWA/MUTCD (Criterios 1 a 4: Volumen, Retraso, Cola, Saturación). |
| 📈 **[MFD y Analítica de Red de Tráfico](mfd_and_analytics.md)** | Física Macroscópica | Regresiones del Diagrama Fundamental Macroscópico (MFD), mitigación de caída de capacidad (capacity drop), control perimetral (perimeter gating) y caché de filtro de incidentes. |
| 🔍 **[IA Explicable (XAI) y SAS](xai_and_sas.md)** | Auditoría Municipal y XAI | Google Captum Integrated Gradients (canalización multiagente en caché), 5 ecuaciones formales y motor de auditoría forense de vetos Guardian. |
| 📄 **[Motor de Bloques de Informes](report_blocks_and_templates.md)** | Generación Automatizada de Informes | Generación Word (.docx) conforme a ABNT NBR 14724 con ecuaciones OMML y `ReportNumberFormatter` con caché por `stat`. |
| 🤖 **[Modelos de Lenguaje Reducidos (SLM)](slm_and_local_llm.md)** | IA Local Privada | Qwen3.5 2B / llama.cpp local serializado mediante `slm_process_lock`, sondeo de VRAM con `pynvml` y `unload()` explícito. |
| 🖥️ **[UI Desktop y Vista de Planificación](ui_and_dashboard.md)** | Arquitectura Frontend | GUI de escritorio en Flet, CCO React 18 (animaciones en compositor y viewport rAF), pausa de `MapAnimator` en ventana oculta y `AuditLogWidget` paginado. |
| 🗺️ **[Renderizado de Mapas Vectoriales y Heatmaps](rendering_and_heatmaps.md)** | Visualización Geoespacial | Caché LRU para `.net.xml` de SUMO (`read_sumo_net_cached`), renderizado offscreen con `mpl_utils` y mapas de calor KDE asíncronos. |
| 🔐 **[Seguridad y Autenticación](security_and_auth.md)** | Gobernanza y Acceso | RBAC, bloqueo PBKDF2 con sal, TLS/mTLS y Bearer en gRPC, Web Gateway *fail-closed* `503` y fijación (*pinning*) de certificados SHA-256. |
| 🛠️ **[Guías para Desarrolladores](developer_guides.md)** | Ingeniería y Extensión | Ajustes `.env` de 12 factores y `[SYNAPSE]`, `CARINA_GATEWAY_ROLE`, protocolos segregados en `src/interfaces/` y agentes personalizados. |
| 🧪 **[Pruebas y Aseguramiento de Calidad](testing.md)** | Control de Calidad y Suite de Pruebas | **967 pruebas Pytest** (935 unitarias, 18 de integración, 14 raíz), **46 pruebas unitarias en Go**, `scripts/pytest_limited.sh` y `tests/memory_guard.py`. |
| 🚀 **[Despliegue y Empaquetado](deployment_and_packaging.md)** | Operaciones y Empaquetado | Compilaciones Docker multietapa, demonios Systemd, Web Gateway *fail-closed* de confianza cero y despliegue con Tailscale Funnel. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
