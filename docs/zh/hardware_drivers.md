---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [硬件驱动程序, 物理信号机, NTCIP 1202, UTMC 集成]
---

# 🚦 硬件驱动程序与现场物理交通机集成

本文档详尽规范了 CARINA 位于 [`src/drivers/`](../../src/drivers) 与 [`src/controller/`](../../src/controller) 的物理底层硬件集成层。深入阐述了工业级通信协议（**NTCIP 1202**、**UTMC / UTMC2**、**SNMP v2c/v3**）、硬件连接生命周期管理、现场遥测数据采集以及确定性故障安全（Fail-Safe）控制权回退机制。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🏛️ 查阅 [多进程架构](architecture.md) | 🛡️ 查阅 [安全机制与看门狗](safety_and_watchdog.md) | 🚑 查阅 [EVP 优先通行](evp_and_preemption.md)

---

## 1. 架构全景概览

CARINA 通过高性能独立编译型 **Go 语言硬件网关**（由 [`src_go/`](../../src_go) 编译生成的 `bin/carina-go`）与现场真实道路交通信号机（如 Econolite、Siemens、Peek、SWARCO、Yunex 等）进行通信交互。CARINA Python 核心控制层与 Go 网关之间的通信完全通过**操作系统标准管道（`stdin`/`stdout`）**以换行符分隔的 JSON（NDJSON）高效运转。这种设计确保了**本地主机零控制网络端口开放**，保障了亚毫秒级指令执行速度，并彻底杜绝了 Python 全局解释器锁（GIL）对通信吞吐的制约。

### 1.1 单一网关所有权 (`CARINA_GATEWAY_ROLE`) 与闭环控制架构
为防止重复启动 `bin/carina-go` 进程、UDP `162` Trap 监听端口冲突以及 SNMP 脑裂状态：
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`)：** 独占派生 `bin/carina-go`，托管 [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py)（由 `GatewayRuntimeWorker`、`HardwareCommandService`、`FenixStageDispatcher` 与 `TailscaleGatewayAdapter` 组成），持有 `HardwareConnectionManager` 本地 SNMP 连接并向下游工作进程广播状态快照。
- **`AI_Process`、`SDS` 与 `UI` (`CARINA_GATEWAY_ROLE=remote`)：** 以远程镜像模式运行，不启动本地 Go 二进制程序也不绑定 UDP `162`。[`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py)（由 [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py) 实例化）通过 [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py) 将动作（`ai_hardware_cmd`）与 EVP 优先通行请求（`ai_evp_preempt`）转发回 `CentralController`。
- **闭环遥测解码：** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) 与 [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) 将控制器实时位掩码（`active_greens`、`active_yellows`、`active_reds`、`current_stage`）反向解码为基于 0 的 SUMO 相位索引，用于 AI 状态提取与 F.E.N.I.X. 交接对账。

除了标准的 NTCIP/UTMC 控制协议外，Go 网关还内嵌了用于微秒级相位保持下发的 **EVP 优先调度器**（`src_go/evp_go/dispatcher.go`），以及提供基于令牌认证的 Tailscale 网格互联、TLS 终止、HTTP 遥测高速摄入（端口 `2201`）和面向 CCO 指挥大屏的服务器发送事件（SSE）实时流的 **远程 Web 网关**（`src_go/web_gateway/server.go`）。

```text
       ┌────────────────────────────────────────────────────────┐
       │     CentralController (CARINA_GATEWAY_ROLE=owner)      │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │ (状态与 SNMPv2/v3)   │   │   │ (心跳看门狗监控)     │
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
                                  │ stdin / stdout (NDJSON IPC - 零本地控制端口)
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
      │  │  EVP 优先调度器  │ │GoSNMP v2/3│ │ 二进制 Trap 解码 │   │
      │  │ (直接 OID 锁定)  │ │UDP 161 端口│ │ (SNMPv1/v2c/v3)  │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ 远程 Web 接入与安全网格
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │       Web 网关与 Tailscale 虚拟网格 (端口 2201 / TLS)     │
      │  - 默认故障安全关闭（未启用时返回 HTTP 503）              │
      │  - POST /api/v1/evp/telemetry (令牌认证, HTTP 204)        │
      │  - GET /cco/stream (令牌认证, CORS, 大屏 SSE)             │
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

### 2.2 标准 OID 映射表 (`src_go/configs/ntcip_oids.json`)

所有 NTCIP 1202 状态 OID（`phaseStatusGroup`）与控制 OID（`phaseControlGroup`）均通过 [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go) 同时支持整数与 `OCTET STRING`/`BitString` PDU 编码，并支持通过 `config_path` 按路口覆盖自定义配置：

| 对象键 (Object Key) | ASN.1 OID 路径 | 分组 / 类型 | 详细语义说明 |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | 状态 / 位掩码 | 当前处于红灯显示状态的相位位掩码。 |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | 状态 / 位掩码 | 当前处于黄灯显示状态的相位位掩码。 |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | 状态 / 位掩码 | 当前处于绿灯显示状态的相位位掩码。 |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | 状态 / 位掩码 | 现场控制器上报的当前有效机动车检测请求。 |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | 状态 / 位掩码 | 现场控制器上报的当前有效行人过街按钮请求。 |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | 控制 / 位掩码 | 屏蔽特定相位，禁止其在当前周期内被放行。 |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | 控制 / 位掩码 | 锁定当前绿灯相位（`ascPhaseControlHold`）。 |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | 控制 / 位掩码 | 强制终止当前绿灯相位（`ascPhaseControlForceOff`）。 |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | 控制 / 位掩码 | 注入模拟机动车检测请求（`ascPhaseControlVehCall`）。 |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | 控制 / 位掩码 | 注入模拟行人过街请求（`ascPhaseControlPedCall`）。 |

---

## 3. UTMC / UTMC2 驱动与 SNMPv3 USM 支持

针对遵循英国**城市交通管理与控制 (UTMC)** 框架或启用认证 **SNMPv3** 现场机柜的交通信号路口：

### 3.1 源码文件架构
**Go 语言网关实现 (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): 原生 Go UTMC 协议通信处理器，提供线程安全的 `Probe()` 与 `CloseTransport()`。
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): 相位确认（`status_active`、`status_leaving`、`status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`、`status_ped_demand`）解析器。
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): 相位需求、保持、强制切断以及支持绿间隔安全保护的逻辑动作执行器。
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): 将 UTMC 相位（Stage 1..8）映射为 CARINA 神经决策动作。
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) 与 [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): 内嵌 UTMC OID 规范定义。
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go): **SNMPv3 USM 引擎**，支持 `NoAuthNoPriv`、`AuthNoPriv` 与 `AuthPriv` 安全级别，认证协议覆盖 `MD5`、`SHA`、`SHA224`、`SHA256`、`SHA384`、`SHA512`，加密协议支持 `DES`、`AES`、`AES192`、`AES256`、`AES192C`、`AES256C`。单路口的 `snmp_config` JSON 元数据及 `config_path` OID 覆盖配置经由 [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) 与 [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) 透传至 [`DriverFactory`](../../src/drivers/driver_factory.py) 与 `GoGatewayClient`。

---

## 4. EVP 硬件优先通行调度器 (`src_go/evp_go/`)

**EVP 优先调度器** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) 负责在亚毫秒级时延内向现场物理控制器下发应急全绿波走廊保持指令：

- **旁路常规推理周期：** 优先通行触发时直接越过常规神经网络动作选择与干道多路口协调周期，直接向目标放行相位注入绿灯保持指令。
- **SNMP OID 保持位注入：** 将目标绿灯相位索引（`stage_idx` 与 `stage_codes`）转换为 NTCIP `phase_control.hold` (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) 或 UTMC 相位保持位掩码，在确保冲突方向持续显示红灯的同时，赋予特勤车辆绝对优先路权。
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

### 6.1 连接生命周期与连接池管理 (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) 与 [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py): 统一维护交通机连接状态机（`DISCONNECTED`、`CONNECTING`、`ONLINE`、`DEGRADED`、`FAILSAFE`）、`remote` 模式下的被动镜像视图（`update_remote_hardware_status`）、仿真器端口自动探测（[`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)）以及 CSV 批量恢复导入（[`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)）。
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) 与 [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py): 在 `hardware_controller_connections` 表和 CSV 模板中持久化 IP 端点及可选的 `snmp_config` JSON（SNMPv3 USM / 自定义 OID `config_path`），并保留 [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) 作为向后兼容的门面接口。
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): 通过 `HardwareGatewayCoordinator.on_failsafe_triggered()` 执行应急回退，并通过 `on_failsafe_recovered()` 实现恢复重联。

### 6.2 确定性故障安全、恢复机制与二进制 SNMP Trap
1. **心跳丢失与可逆故障安全：** 若与现场控制器的通信中断或触发看门狗故障安全机制，`EmergencyReleaseControlAll()` 会暂停心跳并释放所有相位保持锁定，同时保留 SNMP 驱动实例与 Trap 监听器运行，以便在系统恢复后通过 `resume_control`（`ResumeControlAll()`）平滑恢复控制。仅当进程退出或发生 `EOF`/`SIGPIPE` 时，才调用 `ShutdownAll()` 永久释放保持并关闭套接字。
2. **绿间隔保护 (`HardwareStageActuator`)：** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) 在黄灯/全红绿间隔清空期（`_is_intergreen_stage`）自动跳过存在冲突的 `send_stage_hold` 调用，并统一规范化解析带 `tl_` 前缀的路口 ID。
3. **二进制 SNMPv1/v2c/v3 Trap 解码器 (`src_go/pkg/traplistener/snmp_decoder.go`)：** 在 UDP `162` 端口（`CARINA_TRAP_PORT`）解析 ASN.1 BER 二进制 Trap/Inform 数据包，按严重级别（`CRITICAL`、`WARNING`、`INFO`）自动分类 `coldStart`、`warmStart`、`linkDown`、`linkUp`、`authenticationFailure`、NTCIP（`.1206.*`）以及 UTMC（`.13267.*`、`.2825.*`）硬件告警。
4. **安全绿冲突拦截审计：** 所有下发至底层的动作指令在正式派发前均需经过 [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) 的严格校验，审核绿间隔清空时长与物理冲突矩阵。

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
