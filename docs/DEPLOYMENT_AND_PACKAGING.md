---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [Deployment Guide, Packaging, Docker, Systemd]
---

# 🚀 Deployment & Service Configuration

This document details production deployment options for CARINA, including Systemd service setup and environment configuration.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md) | 🗄️ See [Database & Schemas](DATABASE_AND_SCHEMAS.md) | 🧪 See [Testing & Validation](TESTING.md)

---

## 1. Production Docker Containerization (`Dockerfile`)

CARINA includes an optimized multi-stage build `Dockerfile` for GPU-accelerated container execution.

### 1.1 Build Docker Image
```bash
docker build -t carina-core:latest .
```

### 1.2 Run Container with GPU Acceleration
```bash
docker run -d \
  --name carina_app \
  --gpus all \
  -p 50051:50051 \
  -p 8001:8001 \
  -v /var/log/carina:/app/logs \
  carina-core:latest
```

---

## 2. Linux Systemd Daemon Configuration

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

## 3. Packaging & Distribution

Legacy PyInstaller and `.deb` packaging via `build_installer.sh` have been removed. A modern, containerized distribution and installation pipeline is planned for upcoming releases.
