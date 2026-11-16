---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [部署指南, 系统打包, Docker容器化, Systemd服务]
---

# 🚀 系统部署与生产环境服务配置

本文档详尽规范了 CARINA 在生产环境下的部署规范，涵盖网络端口规划、编译构建流程、Docker 容器化、Linux Systemd 守护进程配置以及基于 Tailscale 的安全远程穿透。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🛠️ 查阅 [开发者指南](developer_guides.md) | 🗄️ 查阅 [数据库与模式](database_and_schemas.md) | 🧪 查阅 [测试规范与质量保证](testing.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 网络端口规划与通信参考速查表

CARINA 统筹管理本地多进程通信、现场硬件控制器以及云端大屏展示所使用的专用端口：

| 监听端口 | 传输层协议 | 对应子系统 / 进程 | 功能语义说明 |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | 外部高频 gRPC 服务，支持可选 TLS/mTLS 与 Bearer 令牌认证（`CARINA_GRPC_*`）。 |
| **`8080`** | TCP (WS) | 智能仪表盘服务 (SDS) | 遥测 WebSocket 服务器，具备背压控制与 2.0s 超时保护。 |
| **`2201`** | TCP (HTTP/HTTPS/SSE) | Go Web 网关 (`src_go/web_gateway`) | 可通过 `CARINA_GATEWAY_PORT` 配置；在 `CARINA_GATEWAY_ENABLED=True` 前默认故障安全关闭（`503`），提供令牌与可选 TLS 保护。 |
| **`8085`** | TCP (HTTP/HTTPS) | 独立 EVP 接收器 (`src_go/evp_go`) | 应急特种车辆 GPS 遥测监听器，支持 Bearer/`X-EVP-Token` 认证与 TLS。 |
| **`42123`** | TCP (Local) | 单实例互斥锁 (`single_instance.py`) | 本地操作系统互斥锁，防止应用多开；向下发 `RESTORE` 唤醒信号。 |
| **`161`** | UDP (SNMP) | NTCIP 1202 / UTMC2 交通机 | 仅由 `CARINA_GATEWAY_ROLE=owner`（`CentralController`）独占驱动 SNMPv2c/v3 轮询与相位保持。 |
| **`162`** | UDP (Trap) | 硬件陷阱监听服务器 (`traplistener`) | 可通过 `CARINA_TRAP_PORT` 配置；解码二进制 SNMPv1/v2c/v3 Trap 与 Inform 报文。 |

---

## 2. 核心子系统编译构建流程

在生产环境中正式部署 CARINA 之前，需完成原生二进制网关及 Web 前端资产的编译：

### 2.1 编译 Go 硬件与 Web 通信网关
编译生成的 Go 原生二进制守护进程负责现场交通机 SNMP 轮询、微秒级 EVP 相位锁定以及 CCO 大屏 SSE 流分发：
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 构建 React CCO Web 运营大屏前端
中央控制调度中心 (CCO) 现代化大屏前端位于 [`src_tsx/`](../../src_tsx)：
```bash
cd src_tsx
npm install
npm run build
```
Vite 构建工具将生产静态包输出至 `src_tsx/dist/`，该静态资源由 Go Web 网关在 `http://localhost:2201/cco/` 路由下自动托管交付。

---

## 3. 生产环境 Docker 容器化构建 (`Dockerfile`)

CARINA 提供了经过多阶段构建优化、支持 GPU 硬件加速的标准化 `Dockerfile`：

### 3.1 构建 Docker 镜像
```bash
docker build -t carina-core:latest .
```

### 3.2 启用 GPU 硬件加速与端口映射运行容器
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

## 4. Linux Systemd 系统守护进程配置

在 Ubuntu / Debian Linux 生产服务器上以系统系统守护进程形式运行 CARINA：

创建服务单元文件 `/etc/systemd/system/carina.service`：

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

加载配置并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. 零信任默认关闭网关与 Tailscale Funnel 部署

针对无静态公网 IP 的分布式都市交通边缘机房：
1. 在完成认证令牌与 TLS 证书配置之前，保持 `CARINA_GATEWAY_ENABLED=False`（`.env.example` 与 `config/settings.ini` 中的默认值）；禁用期间，Go Web 网关对 CCO/EVP 端点统一返回 `503 Service Unavailable`。
2. 在 Tailscale 控制台生成具备 `funnel` 授权的 Auth Key，并为 EVP、CCO 与 Synapse gRPC 生成高强度 Bearer 令牌。
3. 配置 `.env` 环境变量：
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
4. `CentralController` 以 `CARINA_GATEWAY_ROLE=owner` 启动（将令牌/TLS 配置转发给 `bin/carina-go`），而 UI/AI/SDS 工作进程以 `remote` 模式运行。[`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) 自动完成节点注册并建立 `https://<node-name>.<tailnet>.ts.net:2201` HTTPS Funnel。

---

## 6. 打包与密封式 Debian 分发 (`.deb`)

CARINA 提供了由 Docker 与 Docker Buildx 驱动的全容器化多阶段密封式构建体系（见 [`scripts/build_deb.sh`](../../scripts/build_deb.sh) 与 [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)）：

- **阶段 1 (前端编译)：** 编译 CCO React/TypeScript Web 地图为高性能生产静态资源包 (`node:20-bookworm-slim`)。
- **阶段 2 (Go 网关构建)：** 原生编译 `bin/carina-go` 二进制文件，无任何外部 CGO 动态依赖 (`golang:1.24-alpine`)。
- **阶段 3 (Python 独立虚拟环境)：** 在 `/opt/carina/venv` 中构建完整的 Python 3.12 隔离运行环境，集成 PyTorch CPU 加速与全套系统依赖 (`ubuntu:24.04`)。
- **阶段 4 (Debian 打包生成)：** 汇集二进制可执行文件、核心配置、systemd 服务单元 (`carina.service`) 与桌面快捷方式，封装生成自包含的标准 Debian 安装包 (`dist/carina_1.0.0_amd64.deb`)。

### 编译安装包
执行以下脚本即可生成干净且具备高度可复现性的安装包：
```bash
./scripts/build_deb.sh
```

### 安装系统包
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # 自动解析可选系统级依赖 (SUMO, libgl1 等)
```
安装器将全自动配置 `/opt/carina`，注册 `carina` systemd 系统服务，并在 `/usr/local/bin/carina` 建立可执行软链接。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
