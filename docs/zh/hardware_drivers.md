---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [硬件驱动程序, 物理信号机, NTCIP 1202, UTMC 集成]
---

# 🚦 硬件驱动程序与现场物理交通机集成

本文档详尽规范了 CARINA 位于 [`src/drivers/`](../../src/drivers) 与 [`src/controller/`](../../src/controller) 的物理底层硬件集成层。深入阐述了工业级通信协议（**NTCIP 1202**、**UTMC / UTMC2**、**SNMP v2c/v3**）、硬件连接生命周期管理、现场遥测数据采集以及确定性故障安全（Fail-Safe）控制权回退机制。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🏛️ 查阅 [多进程架构](architecture.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 架构全景概览

CARINA 通过高性能独立编译型 **Go 语言硬件网关**（由 [`src_go/`](../../src_go) 编译生成的 `bin/carina-go`）与现场真实道路交通信号机（如 Econolite、Siemens、Peek、SWARCO、Yunex 等）进行通信交互。CARINA Python 核心控制层与 Go 网关之间的通信完全通过**操作系统标准管道（`stdin`/`stdout`）**以换行符分隔的 JSON（NDJSON）高效运转。这种设计确保了**本地主机零网络开放端口**，保障了亚毫秒级指令执行速度，并彻底杜绝了 Python 全局解释器锁（GIL）对通信吞吐的制约。

除了标准的 NTCIP/UTMC 控制协议外，Go 网关还内嵌了用于微秒级相位保持下发的 **EVP 优先调度器**（`src_go/evp_go/dispatcher.go`），以及提供 Tailscale 网格互联、HTTP 遥测高速摄入（端口 `2201`）和面向 CCO 指挥大屏的服务器发送事件（SSE）实时流的 **远程 Web 网关**（`src_go/web_gateway/server.go`）。

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │ (连接状态与连接池)   │   │   │ (心跳看门狗监控)     │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │  (优先调度服务)      │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Python 管道子进程管理) │
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - 主机零开放端口)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │            CARINA 硬件通信网关 (Go 编译二进制程序)        │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │    NTCIP 驱动      │         │    UTMC 驱动       │   │
      │   │ (NTCIP 1202 v02)   │         │ (英国 UTMC2 标准)  │   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │  EVP 优先调度器  │ │  GoSNMP  │ │ TrapListener 监听│   │
      │  │ (直接 OID 锁定)  │ │UDP 161 端口│ (UDP 162 端口)   │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ 远程 Web 接入与安全网格
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │          Web 网关与 Tailscale 虚拟网格 (端口 2201)        │
      │  - POST /api/v1/evp/telemetry (HTTP 204 GPS 高速摄入)     │
      │  - GET /cco/stream (大屏实时 SSE 广播发布中心)            │
      │  - Tailscale Funnel / 端到端加密零信任对等网络            │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. NTCIP 1202 感应式信号机 (ASC) 驱动

**NTCIP 1202 标准**（ITS 国家交通通信协议）是北美及全球现代智能交通系统中应用最广泛的开放标准。

### 2.1 源码文件架构
**Go 语言网关实现 (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go): 原生 Go NTCIP 驱动主编排器。
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go): 当前活动相位、环状态以及检测器触发状态的遥测轮询器。
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go): 相位保持（Phase Hold）、强制切断（Force-Off）与相位请求（Phase Call）执行引擎。
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go): 将 CARINA 离散控制动作转换为 NTCIP 相位位掩码。
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) 与 [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json): 内嵌 OID 结构配置字典。

**Python 桥接与代理层 (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py): NDJSON 匿名管道 IPC 客户端，负责驱动与管理 `bin/carina-go` 子进程。
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py): 即插即用的 `BaseTrafficDriver` 代理，透明转发指令至 Go 守护进程。
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py): 根据品牌与型号自动探测实例化对应的驱动代理。

### 2.2 标准 OID 映射表

| 对象名称 (Object Name) | ASN.1 OID 路径 | 数据类型 | 详细语义说明 |
| :--- | :--- | :---: | :--- |
| `ascPhaseStatusGroupReds` | `1.3.6.1.4.1.1206.4.2.1.1.1` | `OCTET STRING` | 当前处于红灯显示状态的相位位掩码。 |
| `ascPhaseStatusGroupYellows` | `1.3.6.1.4.1.1206.4.2.1.1.2` | `OCTET STRING` | 当前处于黄灯显示状态的相位位掩码。 |
| `ascPhaseStatusGroupGreens` | `1.3.6.1.4.1.1206.4.2.1.1.3` | `OCTET STRING` | 当前处于绿灯显示状态的相位位掩码。 |
| `ascPhaseHold` | `1.3.6.1.4.1.1206.4.2.1.1.5` | `OCTET STRING` | 锁定当前绿灯相位（阻止发生相位切换）。 |
| `ascPhaseForceOff` | `1.3.6.1.4.1.1206.4.2.1.1.6` | `OCTET STRING` | 强制终止当前绿灯相位，提前进入过渡清空。 |
| `ascPhaseCall` | `1.3.6.1.4.1.1206.4.2.1.1.7` | `OCTET STRING` | 注入模拟车辆检测信号，主动请求特定相位。 |

---

## 3. UTMC / UTMC2 驱动 (英国国家标准)

针对遵循英国**城市交通管理与控制 (UTMC)** 框架的交通信号路口：

### 3.1 源码文件架构
**Go 语言网关实现 (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): 原生 Go UTMC 协议通信处理器。
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): 相位确认（Stage Confirmation）与应答帧解析器。
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): 相位需求（Stage Demand）与相位切换指令执行器。
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): 将 UTMC 相位（Stage 1..8）映射为 CARINA 神经决策动作。
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) 与 [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): 内嵌 UTMC OID 规范定义。

---

## 4. EVP 硬件优先通行调度器 (`src_go/evp_go/`)

**EVP 优先调度器** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) 负责在亚毫秒级时延内向现场物理控制器下发应急全绿波走廊保持指令：

- **旁路常规推理周期：** 优先通行触发时直接越过常规神经网络动作选择与干道多路口协调周期，直接向目标放行相位注入绿灯保持指令。
- **SNMP OID 保持位注入：** 将目标绿灯相位索引转换为 NTCIP `ascPhaseHold` (`1.3.6.1.4.1.1206.4.2.1.1.5`) 位掩码，在确保冲突方向持续显示红灯的同时，赋予特勤车辆绝对优先路权。
- **微秒级 IPC 管道通信协议：** 通过操作系统匿名管道下发 `evp_preempt` NDJSON 指令驱动：
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **故障安全看门狗与保持释放：** 当车辆驶越驶离门限（$\le 15\text{ m}$）或达到最大驻留看门狗时限（$45\text{ s}$）时，系统自动释放保持。若网关发生异常崩溃或网络断开，现场物理控制器在连续丢失 3 次心跳后会自动解除外部锁定。

---

## 5. 远程 Web 网关与虚拟网络网格 (`src_go/web_gateway/`)

针对特勤车辆或远程运维中心需要在不暴露公网 IP 的前提下实现跨网段接入的分布式智慧城市场景：

- **Tailscale 加密网格网络：** 深度集成 [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go)，使位于城市边缘机房的 CARINA 信号控制器能够构建端到端强加密的零信任覆盖网络。
- **Tailscale Funnel（端口 2201）：** 在无需配置局域网路由器端口转发或开放本地防火墙端口的前提下，安全地通过公网 TLS 对外暴露高并发接入端点。
- **高吞吐量车载遥测接收器：** 暴露 `POST /api/v1/evp/telemetry`（HTTP 204 即发即弃模式），以亚毫秒级响应延迟摄入高频车载 GPS 定位信标。
- **服务器发送事件 (SSE) 广播发布中心：** [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) 通过 `GET /cco/stream` 向中央控制调度中心（CCO）运营大屏实时单向推送全城路口运行遥测、特勤车辆轨迹及信号灯实时状态。

---

## 6. 硬件连接管理与故障安全回退机制

### 6.1 连接生命周期与连接池管理 (`src/controller/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py): 统一维护交通机连接状态机（`DISCONNECTED`、`CONNECTING`、`ONLINE`、`DEGRADED`、`FAILSAFE`）。
- [`src/controller/connection_config_repo.py`](../../src/controller/connection_config_repo.py): 在 `hardware_controller_connections` 数据库表中安全持久化存储 IP 地址、通信端口、协议类型及访问凭据。
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): 执行确定性故障安全应急回退。

### 6.2 确定性故障安全回退逻辑
1. **心跳丢失判定 (< 500 ms)：** 一旦与现场控制器的通信在连续 3 个轮询周期内未收到有效应答，CARINA 立即主动撤销所有相位保持（Phase Holds）与强制切断（Force-Off）指令。
2. **控制器本地自主接管：** 物理控制器瞬间无缝回退至其内置的本地协调定时配时方案（日时段方案 / 黄闪模式），绝对保障交叉口的交通安全底线。
3. **安全绿冲突拦截审计：** 所有下发至底层的动作指令在正式派发前均需经过 [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) 的严格校验，审核绿间隔清空时长与物理冲突矩阵。

### 6.3 硬件异常事件上报与告警防抖去重 (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py): 实时捕获交通机硬件状态跃迁（`CONNECTING`、`ONLINE`、`DEGRADED`、`FAILSAFE`），格式化构造标准化的异常事件 JSON 报文。
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py): 通过基于时间戳防抖的有状态哈希缓存消除告警风暴，将已拦截哈希持久化于 `.carina_incident_filter_cache.json`。
- 通过 `MonitorClient` 将告警消息动态分发至配置的外部监控传输通道（本地 MQTT Broker 或远程 HTTP/Ngrok 端点）。

---

## 7. 安全配置与网络机密凭证管理

严禁在代码中硬编码任何硬件通信机密。CARINA 通过在 [`.env`](../../.env.example) 文件中声明的环境变量动态解析 SNMP 团体名与控制器身份凭据：

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

关于系统安全配置与用户角色权限划分，请参阅 [安全机制与身份认证](security_and_auth.md)。
关于遥测报文序列化模式的详细规范，请参阅 [API 接口参考](api_reference.md)。

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
