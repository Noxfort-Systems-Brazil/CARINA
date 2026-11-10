---
tags: [implantacao, empacotamento, docker, debian, systemd]
aliases: [Guia de Implantação, Empacotamento, Docker, Systemd]
---

# 🚀 Implantação & Configuração de Serviços

Este documento detalha as opções de implantação em produção do ecossistema CARINA, incluindo configuração de serviços Systemd, containerização Docker e malhas de comunicação de rede.

⬅️ [Central de Documentação](carina_moc.md) | 🛠️ [Guias de Desenvolvimento](developer_guides.md) | 🗄️ [Banco de Dados & Esquemas](database_and_schemas.md) | 🧪 [Testes e Validação](testing.md) | 🚑 [Preempção de Emergência (EVP)](evp_and_preemption.md)

---

## 1. Tabela de Portas de Rede & Comunicação

O CARINA coordena pipelines multiprocesso locais, controladores de hardware de campo e videowalls em nuvem através de portas dedicadas:

| Porta | Protocolo | Subsistema / Processo | Descrição |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | Servidor gRPC de alta frequência externo para simuladores microscópicos (SUMO/CityFlow) ou ingestão de sensores/visão. |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Servidor WebSocket de telemetria transmitindo filas e estados em tempo real para clientes web. |
| **`2201`** | TCP (HTTP/SSE) | Go Web Gateway (`src_go/web_gateway`) | Ingress primário de borda: `POST /api/v1/evp/telemetry` (HTTP 204), `GET /cco/stream` (SSE) e dashboard CCO. |
| **`8085`** | TCP (HTTP) | Receptor EVP Autônomo (`src/evp`) | Receptor HTTP alternativo de telemetria GPS de viaturas de emergência quando o gateway Go está inativo. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | Mutex de sistema operacional impedindo instâncias duplicadas; transmite sinal `RESTORE`. |
| **`161`** | UDP (SNMP) | Controladores de Campo NTCIP 1202 / UTMC | Sondagem e comando de retenção de fase (`ascPhaseHold`) enviados aos controladores semafóricos. |
| **`162`** | UDP (Trap) | Hardware Trap Listener (`traplistener`) | Ingestão assíncrona de traps de falhas de hardware e atuações de detectores de laço. |

---

## 2. Compilação dos Subsistemas Principais

Antes de implantar o CARINA em produção, os binários nativos e artefatos web devem ser compilados:

### 2.1 Compilando o Gateway Go de Hardware e Web
O daemon Go compilado gerencia a sondagem SNMP de controladores físicos, comandos de preempção EVP em microssegundos e streaming para o videowall CCO:
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 Compilando o Dashboard Web CCO (React / TSX)
A interface web da Central de Controle Operacional (CCO) está localizada em [`src_tsx/`](../../src_tsx):
```bash
cd src_tsx
npm install
npm run build
```
O Vite gera os pacotes de produção em `src_tsx/dist/`, servidos automaticamente pelo Go Web Gateway no endereço `http://localhost:2201/cco/`.

---

## 3. Containerização Docker para Produção (`Dockerfile`)

O CARINA disponibiliza um `Dockerfile` otimizado com compilação multi-estágio para execução em contêiner com aceleração por GPU:

### 3.1 Construir Imagem Docker
```bash
docker build -t carina-core:latest .
```

### 3.2 Executar Contêiner com Aceleração GPU & Portas de Rede
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

## 4. Configuração como Daemon Linux Systemd

Para executar o CARINA como serviço de segundo plano gerenciado pelo Systemd no Ubuntu/Debian Linux:

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

Habilite e inicie o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. Implantação em Malha Zero-Trust via Tailscale Funnel

Para redes metropolitanas distribuídas sem endereços IP públicos estáticos:
1. Gere uma chave de autenticação Tailscale (Auth Key) com capacidade de `funnel` no console administrativo do Tailscale.
2. Configure o arquivo `.env`:
   ```bash
   CARINA_GATEWAY_ENABLED=true
   CARINA_GATEWAY_PORT=2201
   CARINA_TAILSCALE_AUTH_KEY=tskey-auth-kXXXXX-XXXXXXXX
   ```
3. Ao iniciar o Gateway Go, [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) registra o nó automaticamente e estabelece um túnel HTTPS Funnel em `https://<nome-do-no>.<tailnet>.ts.net:2201`, expondo a API de telemetria EVP e o videowall CCO via TLS público sem exigir alterações no firewall municipal.

---

## 6. Empacotamento e Distribuição Hermética Debian (`.deb`)

O CARINA disponibiliza um gerador hermético multi-estágio baseado em Docker e Docker Buildx ([`scripts/build_deb.sh`](../../scripts/build_deb.sh) e [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)):

- **Estágio 1 (Frontend):** Compila a interface web CCO em React/TypeScript em artefatos de produção (`node:20-bookworm-slim`).
- **Estágio 2 (Go Gateway):** Compila `bin/carina-go` nativamente sem dependências CGO (`golang:1.24-alpine`).
- **Estágio 3 (Virtualenv Python):** Configura um ambiente isolado em `/opt/carina/venv` com Python 3.12, acelerações de CPU do PyTorch e todas as dependências (`ubuntu:24.04`).
- **Estágio 4 (Empacotador Debian):** Empacota binários, configurações, serviços systemd (`carina.service`) e atalhos de desktop em um pacote Debian auto-contido (`dist/carina_1.0.0_amd64.deb`).

### Compilando o Pacote
Para gerar um instalador limpo e reproduzível:
```bash
./scripts/build_deb.sh
```

### Instalando o Pacote
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # Resolve dependências opcionais do sistema (SUMO, libgl1, etc.)
```
O instalador configura automaticamente `/opt/carina`, registra o serviço `carina` no systemd e disponibiliza o binário no PATH do sistema (`/usr/local/bin/carina`).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
