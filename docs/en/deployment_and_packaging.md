---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [Deployment Guide, Packaging, Docker, Systemd]
---

# 🚀 Deployment & Service Configuration

This document details production deployment options for CARINA, including Systemd service setup and environment configuration.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🛠️ See [Developer Guides](developer_guides.md) | 🗄️ See [Database & Schemas](database_and_schemas.md) | 🧪 See [Testing & Validation](testing.md) | 🚑 See [EVP Preemption](evp_and_preemption.md)

---

## 1. Network Ports & Communication Reference

CARINA coordinates local multiprocessing pipelines, hardware controllers, and cloud videowalls using dedicated ports:

| Port | Protocol | Subsystem / Process | Description |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | External high-frequency gRPC server with optional TLS/mTLS & Bearer token auth (`CARINA_GRPC_*`). |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Telemetry WebSocket server streaming live queue data with backpressure & 2.0s timeouts. |
| **`2201`** | TCP (HTTP/HTTPS/SSE) | Go Web Gateway (`src_go/web_gateway`) | Configurable via `CARINA_GATEWAY_PORT`; fails closed (`503`) until `CARINA_GATEWAY_ENABLED=True`; protects endpoints with tokens & optional TLS. |
| **`8085`** | TCP (HTTP/HTTPS) | Standalone EVP Receiver (`src_go/evp_go`) | Emergency vehicle GPS telemetry listener supporting Bearer/`X-EVP-Token` auth & TLS. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | OS mutex preventing duplicate application instances; sends `RESTORE` signal. |
| **`161`** | UDP (SNMP) | NTCIP 1202 / UTMC2 Controllers | SNMPv2c/v3 polling and phase holds driven exclusively by `CARINA_GATEWAY_ROLE=owner` (`CentralController`). |
| **`162`** | UDP (Trap) | Hardware Trap Listener (`traplistener`) | Configurable via `CARINA_TRAP_PORT`; decodes binary SNMPv1/v2c/v3 Traps & Informs. |

---

## 2. Building Core Subsystems

Before deploying CARINA in production, native binaries and web assets must be built:

### 2.1 Compiling Go Hardware & Web Gateway
The compiled Go daemon handles physical controller SNMP polling, microsecond EVP preemption holds, and CCO videowall streaming:
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 Building React CCO Web Dashboard
The Central Control Operator (CCO) web interface resides in [`src_tsx/`](../../src_tsx):
```bash
cd src_tsx
npm install
npm run build
```
Vite outputs production bundles into `src_tsx/dist/`, which are automatically served by the Go Web Gateway at `http://localhost:2201/cco/`.

---

## 3. Production Docker Containerization (`Dockerfile`)

CARINA includes an optimized multi-stage build `Dockerfile` for GPU-accelerated container execution:

### 3.1 Build Docker Image
```bash
docker build -t carina-core:latest .
```

### 3.2 Run Container with GPU Acceleration & Network Ports
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

## 4. Linux Systemd Daemon Configuration

To run CARINA as a system daemon on Ubuntu/Debian Linux:

Create `/etc/systemd/system/carina.service`:

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

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. Zero-Trust Fail-Closed Gateway & Tailscale Funnel Deployment

For distributed metropolitan networks without public static IPs:
1. Keep `CARINA_GATEWAY_ENABLED=False` (default in `.env.example` and `config/settings.ini`) until auth tokens and TLS certificates are provisioned; while disabled, the Go Web Gateway serves `503 Service Unavailable` on CCO/EVP endpoints.
2. Generate a Tailscale Auth Key with `funnel` capabilities from the Tailscale Admin Console and strong Bearer tokens for EVP, CCO, and Synapse gRPC.
3. Configure `.env`:
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
4. `CentralController` boots with `CARINA_GATEWAY_ROLE=owner` (forwarding tokens/TLS settings to `bin/carina-go`), while UI/AI/SDS workers run as `remote`. [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) registers the node and spins up an HTTPS Funnel at `https://<node-name>.<tailnet>.ts.net:2201`.

---

## 6. Packaging & Hermetic Debian Distribution (`.deb`)

CARINA provides a containerized, multi-stage hermetic builder powered by Docker and Docker Buildx ([`scripts/build_deb.sh`](../../scripts/build_deb.sh) and [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)):

- **Stage 1 (Frontend):** Compiles the CCO React/TypeScript web map into production bundles (`node:20-bookworm-slim`).
- **Stage 2 (Go Gateway):** Compiles `bin/carina-go` natively with zero CGO dependencies (`golang:1.24-alpine`).
- **Stage 3 (Python Virtualenv):** Configures an isolated `/opt/carina/venv` runtime with Python 3.12, PyTorch CPU optimizations, and all system dependencies (`ubuntu:24.04`).
- **Stage 4 (Debian Packager):** Packages binaries, configs, systemd services (`carina.service`), and desktop entries into a self-contained Debian package (`dist/carina_1.0.0_amd64.deb`).

### Building the Package
To compile a clean, reproducible installation package:
```bash
./scripts/build_deb.sh
```

### Installing the Package
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # Resolves optional system-level dependencies (SUMO, libgl1, etc.)
```
The installer automatically sets up `/opt/carina`, registers the `carina` systemd service, and links the CLI runner to `/usr/local/bin/carina`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
