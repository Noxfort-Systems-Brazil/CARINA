---
tags: [despliegue, empaquetado, docker, debian, systemd]
aliases: [Guía de Despliegue, Empaquetado, Docker, Systemd]
---

# 🚀 Despliegue y Configuración de Servicios

Este documento detalla las opciones de despliegue en producción para CARINA, incluyendo la configuración de servicios con Systemd, contenedores Docker y variables de entorno.

⬅️ Volver al [Hub Maestro de Documentación](carina_moc.md) | 🛠️ Ver [Guías para Desarrolladores](developer_guides.md) | 🗄️ Ver [Base de Datos y Esquemas](database_and_schemas.md) | 🧪 Ver [Pruebas y Validación](testing.md) | 🚑 Ver [Preempción EVP](evp_and_preemption.md)

---

## 1. Referencia de Puertos de Red y Comunicación

CARINA coordina tuberías de multiprocesamiento local, controladores de hardware y videowalls en la nube mediante puertos dedicados:

| Puerto | Protocolo | Subsistema / Proceso | Descripción |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | Servidor gRPC externo de alta frecuencia con TLS/mTLS y autenticación por token Bearer opcionales (`CARINA_GRPC_*`). |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Servidor WebSocket de telemetría transmitiendo datos de cola en vivo con contrapresión (*backpressure*) y timeouts de 2.0s. |
| **`2201`** | TCP (HTTP/HTTPS/SSE) | Gateway Web en Go (`src_go/web_gateway`) | Configurable vía `CARINA_GATEWAY_PORT`; opera *fail-closed* (`503`) hasta `CARINA_GATEWAY_ENABLED=True`; protege endpoints con tokens y TLS opcional. |
| **`8085`** | TCP (HTTP/HTTPS) | Receptor Autónomo EVP (`src_go/evp_go`) | Receptor de telemetría GPS de vehículos de emergencia con soporte para autenticación Bearer/`X-EVP-Token` y TLS. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | Mutex a nivel de SO para prevenir instancias duplicadas; envía la señal `RESTORE`. |
| **`161`** | UDP (SNMP) | Controladores NTCIP 1202 / UTMC2 | Sondeo SNMPv2c/v3 y retenciones de fase controladas exclusivamente por `CARINA_GATEWAY_ROLE=owner` (`CentralController`). |
| **`162`** | UDP (Trap) | Receptor de Traps de Hardware (`traplistener`) | Configurable vía `CARINA_TRAP_PORT`; decodifica Traps e Informs binarios SNMPv1/v2c/v3. |

---

## 2. Compilación de Subsistemas Centrales

Antes de desplegar CARINA en entornos de producción, deben compilarse los binarios nativos y los activos web:

### 2.1 Compilación del Gateway de Hardware y Web en Go
El demonio compilado en Go gestiona el sondeo SNMP a controladores físicos, las retenciones de preempción EVP en microsegundos y el streaming para el videowall CCO:
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 Compilación del Panel Web React para el CCO
La interfaz web del Operador del Centro de Control (CCO) reside en [`src_tsx/`](../../src_tsx):
```bash
cd src_tsx
npm install
npm run build
```
Vite genera los paquetes de producción en `src_tsx/dist/`, los cuales son servidos automáticamente por el Gateway Web en Go en `http://localhost:2201/cco/`.

---

## 3. Contenerización Docker para Producción (`Dockerfile`)

CARINA incluye un `Dockerfile` optimizado con compilación multi-etapa para ejecución acelerada por GPU:

### 3.1 Construir la Imagen de Docker
```bash
docker build -t carina-core:latest .
```

### 3.2 Ejecutar Contenedor con Aceleración por GPU y Mapeo de Puertos
```bash
docker run -d \
  --name carina_app \
  --gpus all \
  -p 50051:50051 \
  -p 8080:8080 \
  -p 2201:2201 \
  -p 8085:8085 \
  -v /var/log/carina:/app/logs \
  -v /etc/carina:/app/config \
  carina-core:latest
```

---

## 4. Configuración del Demonio Systemd en Linux

Para ejecutar CARINA como un servicio daemon del sistema en Ubuntu/Debian Linux:

Cree el archivo `/etc/systemd/system/carina.service`:

```ini
[Unit]
Description=CARINA AI Real-Time Traffic Orchestrator
After=network.target postgresql.service

[Service]
Type=simple
User=carina
WorkingDirectory=/opt/carina
ExecStart=/usr/bin/python3 /opt/carina/carina.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Habilite e inicie el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. Despliegue de Gateway Fail-Closed de Confianza Cero y Tailscale Funnel

Para redes metropolitanas distribuidas sin direcciones IP públicas estáticas:
1. Mantenga `CARINA_GATEWAY_ENABLED=False` (predeterminado en `.env.example` y `config/settings.ini`) hasta que se aprovisionen los tokens de autenticación y los certificados TLS; mientras esté deshabilitado, el Gateway Web en Go responde `503 Service Unavailable` en los endpoints CCO/EVP.
2. Genere una Auth Key de Tailscale con capacidades de `funnel` desde la Consola de Administración de Tailscale y tokens Bearer robustos para EVP, CCO y Synapse gRPC.
3. Configure el archivo `.env`:
   ```bash
   CARINA_GATEWAY_ENABLED=True
   CARINA_GATEWAY_PORT=2201
   CARINA_TRAP_PORT=162
   CARINA_EVP_AUTH_TOKEN=<strong-evp-token>
   CARINA_CCO_AUTH_TOKEN=<strong-cco-token>
   CARINA_CCO_ALLOWED_ORIGIN=https://<node-name>.<tailnet>.ts.net
   CARINA_GATEWAY_TLS_CERT=/etc/carina/certs/gateway.crt
   CARINA_GATEWAY_TLS_KEY=/etc/carina/certs/gateway.key
   CARINA_GRPC_AUTH_TOKEN=<strong-grpc-token>
   CARINA_GRPC_TLS_ENABLED=True
   CARINA_OUTPUT_DIR=/var/lib/carina
   CARINA_CONFIG_DIR=/etc/carina
   CARINA_TAILSCALE_AUTH_KEY=tskey-auth-kXXXXX-XXXXXXXX
   ```
4. `CentralController` arranca con `CARINA_GATEWAY_ROLE=owner` (reenviando tokens y configuración TLS a `bin/carina-go`), mientras que los workers UI/AI/SDS se ejecutan como `remote`. [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) registra el nodo y activa un Funnel HTTPS en `https://<node-name>.<tailnet>.ts.net:2201`.

---

## 6. Empaquetado y Distribución Hermética Debian (`.deb`)

CARINA ofrece un generador hermético multietapa basado en Docker y Docker Buildx ([`scripts/build_deb.sh`](../../scripts/build_deb.sh) y [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)):

- **Etapa 1 (Frontend):** Compila el mapa web CCO en React/TypeScript en bundles de producción (`node:20-bookworm-slim`).
- **Etapa 2 (Go Gateway):** Compila `bin/carina-go` de forma nativa sin dependencias CGO (`golang:1.24-alpine`).
- **Etapa 3 (Virtualenv Python):** Configura un entorno aislado en `/opt/carina/venv` con Python 3.12, optimizaciones CPU de PyTorch y todas las dependencias del sistema (`ubuntu:24.04`).
- **Etapa 4 (Empaquetador Debian):** Empaqueta binarios, configuraciones, servicios systemd (`carina.service`) y accesos directos en un paquete Debian autocontenido (`dist/carina_1.0.0_amd64.deb`).

### Compilación del Paquete
Para compilar un paquete de instalación limpio y reproducible:
```bash
./scripts/build_deb.sh
```

### Instalación del Paquete
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # Resuelve dependencias opcionales del sistema (SUMO, libgl1, etc.)
```
El instalador configura automáticamente `/opt/carina`, registra el servicio `carina` en systemd y enlaza el ejecutable CLI a `/usr/local/bin/carina`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Ingeniería de Movilidad Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado bajo AGPLv3 o posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
