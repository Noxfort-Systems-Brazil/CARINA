---
tags: [implantacao, empacotamento, docker, debian, systemd]
aliases: [Guia de Implantação, Empacotamento, Docker, Systemd]
---

# 🚀 Implantação e Configuração de Serviços em Produção

Este documento detalha as opções de implantação em ambiente de produção do CARINA, abrangendo containerização com aceleração por GPU via Docker, daemons de inicialização do Systemd no Linux e configurações de ambiente.

⬅️ [Central de Documentação](README.md) | 🛠️ [Guias de Desenvolvimento](developer_guides.md) | 🗄️ [Banco de Dados e Schemas](database_and_schemas.md) | 🧪 [Testes e Validação](testing.md)

---

## 1. Containerização com Docker em Produção (`Dockerfile`)

O CARINA inclui um `Dockerfile` multi-stage otimizado para execução isolada em servidores e clusters com aceleração por hardware NVIDIA (CUDA/TensorCores).

### 1.1 Construir Imagem Docker
```bash
docker build -t carina-core:latest .
```

### 1.2 Executar Container com Aceleração por GPU
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

## 2. Configuração de Daemon Systemd no Linux

Para executar o CARINA como serviço nativo de sistema operacional em distribuições Ubuntu/Debian Linux:

Crie o arquivo `/etc/systemd/system/carina.service`:

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

Habilite e inicialize o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 3. Empacotamento e Distribuição

Os scripts legados de empacotamento desktop via PyInstaller e geração de `.deb` monolítico (`build_installer.sh`) foram descontinuados para garantir reprodutibilidade, segurança de contêineres e auditoria contínua de segurança.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Operações e Infraestrutura • CARINA CORE v1.2.0</i>
</div>
