<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — 技术文档套件
### 系统架构、硬件集成与安全框架
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **语言 / Translations:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](README.md)** • **[📚 文档中心](../index.md)**

---

</div>

## 欢迎查阅官方技术文档

本目录包含 **CARINA**（Controlled Artificial Road-traffic Intelligence Network Architecture，受控人工道路交通智能网络架构）的规范中文文档套件 —— 一个专为分布式城市交通信号灯控制设计的高性能企业级深度强化学习生态系统。

## 技术指南目录

| 文档 | 主题 | 核心内容 |
|---|---|---|
| 📚 **[核心主索引 (MOC)](carina_moc.md)** | 主索引与知识图谱 | 代码库全景概览、架构目录层级结构以及 Obsidian 双向引用图谱。 |
| 📖 **[系统架构](architecture.md)** | 核心架构 | 8个操作系统并发微服务、`CARINA_GATEWAY_ROLE` 单一所有者、ST-GATv2 Lite、iTransformer PAE 与 QR-D3QN。 |
| 🚑 **[应急车辆优先 (EVP)](evp_and_preemption.md)** | 应急车辆优先通行 | 自主绿波通道、Haversine 运动学门限 ($60\text{--}160\text{ m}$)、跨进程同步与令牌保护的 Web 网关（端口 2201）。 |
| 🔌 **[硬件驱动与 Go 网关](hardware_drivers.md)** | 现场控制器 | 单一所有者 Go 网关 (`carina-go`)、NDJSON 管道 IPC、NTCIP 1202 (`.4.1.*`/`.5.1.*`)、UTMC2、SNMPv3 USM、闭环相位解码与二进制 Trap。 |
| 🛡️ **[安全架构、看门狗与 FENIX](safety_and_watchdog.md)** | 神经符号双重安全 | `PhysicalActionMasker`、符号否决规则 (SR-00 至 SR-06)、QR-D3QN + Noisy-OR `CHILD` 校准、看门狗与 F.E.N.I.X. 闭环交接。 |
| ⚡ **[Synapse HFT API 与 IPC 队列](api_reference.md)** | 高频通信接口 | Synapse HFT gRPC（TLS/mTLS 与 Bearer 认证，端口 50051）、12个有界 IPC 队列 + 1个线程安全管道与证书固定 CCO 广播。 |
| 🗄️ **[数据库架构与模式](database_and_schemas.md)** | 持久化与关系模式 | PostgreSQL 增量存储（**存储缩减 97.9%**）、`PostgresConnectionPool`、SQLite WAL、`make_interval` SQL 与 168小时 EVP 保留策略。 |
| 🧠 **[神经研究与公式推导](research_notes.md)** | 数学建模 | 统一 TCN (`GroupNorm` + `SiLU`)、`torch.vmap` 批处理、iTransformer PAE、QR-D3QN + Noisy-OR、ST-GATv2 CTDE 与二元 DA SILVA ($\ln 2$)。 |
| 🚦 **[交通信号设置依据 (MUTCD)](traffic_engineering_warrants.md)** | 交通工程学 | 针对 FHWA/MUTCD 法定交通信号控制依据（依据 1 至 4：车流量、延误、排队长度、饱和度）的算法级工程评估。 |
| 📈 **[宏观基础图 (MFD) 与路网分析](mfd_and_analytics.md)** | 宏观交通流物理学 | 宏观基础图 (MFD) 多项式回归、通行能力骤降抑制、边界门控控制以及突发事件滤波缓存。 |
| 🔍 **[可解释人工智能 (XAI) 与 SAS](xai_and_sas.md)** | 市政审计与可解释性 | Google Captum 积分梯度（缓存多智能体管线）、5个形式化数学公式与 Guardian 否决法医级取证审计引擎。 |
| 📄 **[报告模块引擎](report_blocks_and_templates.md)** | 自动化报告生成 | 符合 ABNT NBR 14724 规范的 Word (.docx) 生成，支持 OMML 公式与基于 stat 缓存的 `ReportNumberFormatter`。 |
| 🤖 **[端侧轻量大模型 (SLM)](slm_and_local_llm.md)** | 离线私有化 AI | 基于 `slm_process_lock` 串行化的本地 Qwen3.5 2B / llama.cpp、`pynvml` 显存探测与显式 `unload()`。 |
| 🖥️ **[桌面 UI 与路网规划视图](ui_and_dashboard.md)** | 前端交互架构 | Flet 桌面图形界面、React 18 CCO（合成器动画与 rAF 视口）、`MapAnimator` 窗口暂停与分页 `AuditLogWidget`。 |
| 🗺️ **[矢量地图渲染与热力图](rendering_and_heatmaps.md)** | 地理空间可视化 | SUMO `.net.xml` LRU 缓存 (`read_sumo_net_cached`)、离屏 `mpl_utils` 渲染与异步 KDE 热力图。 |
| 🔐 **[安全机制与身份认证](security_and_auth.md)** | 系统治理与访问控制 | RBAC、加盐 PBKDF2 锁定防护、gRPC TLS/mTLS 与 Bearer 认证、默认关闭（`503`）的 Web 网关与 SHA-256 证书固定。 |
| 🛠️ **[开发者指南](developer_guides.md)** | 工程规范与功能扩展 | 12-Factor `.env` 与 `[SYNAPSE]` 配置、`CARINA_GATEWAY_ROLE`、`src/interfaces/` 隔离协议与自定义智能体开发。 |
| 🧪 **[测试规范与质量保证](testing.md)** | 质量保证与测试套件 | **967 个 Pytest 测试**（935 个单元测试、18 个集成测试、14 个根目录测试）、**46 个 Go 单元测试**、`scripts/pytest_limited.sh` 与 `tests/memory_guard.py`。 |
| 🚀 **[部署与打包发布](deployment_and_packaging.md)** | 运维部署与打包 | 多阶段 Docker 构建、Systemd 守护进程、零信任默认关闭 Web 网关与 Tailscale Funnel 部署。 |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
