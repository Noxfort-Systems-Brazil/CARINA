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
| 📖 **[Arquitectura del Sistema](architecture.md)** | Arquitectura Central | 8 microservicios concurrentes del SO, atención en grafos ST-GATv2 Lite, PAE Universal y aceleración Universal AMP. |
| 🚑 **[Preempción de Emergencia (EVP)](evp_and_preemption.md)** | Preempción de Vehículos de Emergencia | Corredores verdes autónomos, compuertas cinemáticas Haversine de entrada/salida ($60\text{--}160\text{ m}$), Tailscale Web Gateway (puerto 2201) y videowall CCO React. |
| 🔌 **[Controladores de Hardware y Gateway Go](hardware_drivers.md)** | Controladores de Campo | Gateway de hardware industrial en Go (`carina-go`), IPC sin puertos vía tuberías NDJSON, NTCIP 1202, UTMC2, pool de clientes SNMP y fail-safe atómico. |
| 🛡️ **[Arquitectura de Seguridad, Watchdog y FENIX](safety_and_watchdog.md)** | Seguridad Neuro-Simbólica | Reglas de veto simbólico (SR-00 a SR-06), vetos D3QN Guardian contra desbordamiento (spillback), Watchdog en tiempo real (< 500 ms) y auto-resurrección F.E.N.I.X. |
| ⚡ **[API Synapse HFT y Colas IPC](api_reference.md)** | Interfaz de Alta Frecuencia | Interfaz gRPC de sub-milisegundo Synapse HFT (puerto 50051), 11 canales IPC acotados, 1 tubería dúplex y transportes polimórficos de telemetría. |
| 🗄️ **[Arquitectura de Base de Datos y Esquemas](database_and_schemas.md)** | Persistencia y Esquemas | Motor de almacenamiento delta asíncrono en PostgreSQL con **97.9% de reducción de almacenamiento**, enums Smallint de 1 byte y `.env` de 12 factores. |
| 🧠 **[Investigación Neuronal y Formulaciones](research_notes.md)** | Modelado Matemático | Convoluciones temporales PPO-TCN, proyecciones latentes PAE, Dueling DQN, ST-GATv2 Lite y currículo DA SILVA. |
| 🚦 **[Criterios de Ingeniería de Tráfico (MUTCD)](traffic_engineering_warrants.md)** | Ingeniería de Tráfico | Evaluación algorítmica de justificaciones semafóricas regulatorias formales FHWA/MUTCD (Criterios 1 a 4: Volumen, Retraso, Cola, Saturación). |
| 📈 **[MFD y Analítica de Red de Tráfico](mfd_and_analytics.md)** | Física Macroscópica | Regresiones del Diagrama Fundamental Macroscópico (MFD), mitigación de caída de capacidad (capacity drop), control perimetral (perimeter gating) y caché de filtro de incidentes. |
| 🔍 **[IA Explicable (XAI) y SAS](xai_and_sas.md)** | Auditoría Municipal y XAI | Google Captum Integrated Gradients, 5 ecuaciones matemáticas formales y motor de auditoría forense de vetos Guardian. |
| 📄 **[Motor de Bloques de Informes](report_blocks_and_templates.md)** | Generación Automatizada de Informes | Generación de documentos Word (.docx) compatibles con normas técnicas (ABNT NBR 14724) con ecuaciones nativas OMML. |
| 🤖 **[Modelos de Lenguaje Reducidos (SLM)](slm_and_local_llm.md)** | IA Local Privada | Inferencia LLM local 100% offline (Qwen3.5 2B / llama.cpp) generando explicaciones forenses textuales sin filtración a la nube. |
| 🖥️ **[UI Desktop y Vista de Planificación](ui_and_dashboard.md)** | Arquitectura Frontend | GUI de escritorio nativa en Flet, vista interactiva de planificación vectorial, gestión en bandeja del sistema (tray) y bloqueo de instancia única (puerto 42123). |
| 🗺️ **[Renderizado de Mapas Vectoriales y Heatmaps](rendering_and_heatmaps.md)** | Visualização Geoespacial | Parser vectorial offline SUMO `.net.xml` y mapas de calor continuos asíncronos en tiempo real mediante Estimación de Densidad de Kernel (KDE). |
| 🔐 **[Seguridad y Autenticación](security_and_auth.md)** | Gobernanza y Acceso | Control de acceso basado en roles (RBAC), hashing PBKDF2 HMAC-SHA256 con sal (100.000 iteraciones), bloqueo contra ataques de fuerza bruta y aislamiento de 12 factores. |
| 🛠️ **[Guías para Desarrolladores](developer_guides.md)** | Ingeniería y Extensión | Configuración del entorno, implementación de agentes neuronales personalizados y arquitectura de configuraciones modulares SOLID. |
| 🧪 **[Pruebas y Aseguramiento de Calidad](testing.md)** | Control de Calidad y Suite de Pruebas | Suite Pytest con 861 pruebas automatizadas, pruebas unitarias nativas en Go (`go test`), mocks de seguridad de Guardian y validación de cobertura. |
| 🚀 **[Despliegue y Empaquetado](deployment_and_packaging.md)** | Operaciones y Empaquetado | Contenedores Docker multi-etapa con aceleración CUDA y unidades de servicio daemon de Linux Systemd. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
