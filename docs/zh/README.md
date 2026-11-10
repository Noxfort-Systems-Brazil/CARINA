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
| 📖 **[系统架构](architecture.md)** | 核心架构 | 8个操作系统并发微服务、ST-GATv2 Lite 图注意力机制、通用 PAE 以及 Universal AMP 硬件加速。 |
| 🚑 **[应急车辆优先 (EVP)](evp_and_preemption.md)** | 应急车辆优先通行 | 自主绿波通道、Haversine 进出运动学门限 ($60\text{--}160\text{ m}$)、Tailscale Web 网关（端口 2201）与 CCO React 大屏指挥显示系统。 |
| 🔌 **[硬件驱动与 Go 网关](hardware_drivers.md)** | 现场控制器 | 工业级编译型 Go 硬件网关 (`carina-go`)、零端口 NDJSON 匿名管道 IPC、NTCIP 1202、UTMC2、SNMP 客户端连接池与原子级故障安全回退。 |
| 🛡️ **[安全架构、看门狗与 FENIX](safety_and_watchdog.md)** | 神经符号双重安全 | 符号否决规则 (SR-00 至 SR-06)、D3QN Guardian 溢流回堵否决、实时看门狗 (< 500 ms) 与 F.E.N.I.X. 自动复活机制。 |
| ⚡ **[Synapse HFT API 与 IPC 队列](api_reference.md)** | 高频通信接口 | 亚毫秒级 Synapse HFT gRPC 接口（端口 50051）、11个有界进程间队列通道、1个双工管道以及多态外部遥测传输。 |
| 🗄️ **[数据库架构与模式](database_and_schemas.md)** | 持久化与关系模式 | PostgreSQL 异步增量差分存储引擎（实现 **97.9% 存储空间缩减**）、1字节 Smallint 枚举与 12-Factor `.env` 配置规范。 |
| 🧠 **[神经研究与公式推导](research_notes.md)** | 数学建模 | PPO-TCN 时序卷积、PAE 隐空间投影、Dueling DQN、ST-GATv2 Lite 以及 DA SILVA 课程学习机制。 |
| 🚦 **[交通信号设置依据 (MUTCD)](traffic_engineering_warrants.md)** | 交通工程学 | 针对 FHWA/MUTCD 法定交通信号控制依据（依据 1 至 4：车流量、延误、排队长度、饱和度）的算法级工程评估。 |
| 📈 **[宏观基础图 (MFD) 与路网分析](mfd_and_analytics.md)** | 宏观交通流物理学 | 宏观基础图 (MFD) 多项式回归、通行能力骤降抑制、边界门控控制以及突发事件滤波缓存。 |
| 🔍 **[可解释人工智能 (XAI) 与 SAS](xai_and_sas.md)** | 市政审计与可解释性 | Google Captum 积分梯度算法、5个形式化数学公式以及 Guardian 否决法医级取证审计引擎。 |
| 📄 **[报告模块引擎](report_blocks_and_templates.md)** | 自动化报告生成 | 符合 ABNT NBR 14724 规范的 Word (.docx) 文档生成，内嵌原生 Office 数学标记语言 (OMML) 公式。 |
| 🤖 **[端侧轻量大模型 (SLM)](slm_and_local_llm.md)** | 离线私有化 AI | 100% 离线本地 LLM 推理（Qwen3.5 2B / llama.cpp），生成司法级法医文本分析，杜绝云端数据泄露。 |
| 🖥️ **[桌面 UI 与路网规划视图](ui_and_dashboard.md)** | 前端交互架构 | 原生 Flet 桌面图形界面、交互式矢量路网规划视图、系统托盘管理与单实例运行锁（端口 42123）。 |
| 🗺️ **[矢量地图渲染与热力图](rendering_and_heatmaps.md)** | 地理空间可视化 | SUMO `.net.xml` 离线矢量解析器与异步实时核密度估计 (KDE) 热力图渲染。 |
| 🔐 **[安全机制与身份认证](security_and_auth.md)** | 系统治理与访问控制 | 基于角色的访问控制 (RBAC)、加盐 PBKDF2 HMAC-SHA256 哈希（100,000次迭代）、防暴力破解锁定机制与 12-Factor 隔离规范。 |
| 🛠️ **[开发者指南](developer_guides.md)** | 工程规范与功能扩展 | 开发环境搭建、自定义神经智能体开发与基于 SOLID 原则的模块化配置架构。 |
| 🧪 **[测试规范与质量保证](testing.md)** | 质量保证与测试套件 | 包含 861 个自动化测试的 Pytest 套件、原生 Go 单元测试 (`go test`)、Guardian 安全模拟桩与覆盖率验证。 |
| 🚀 **[部署与打包发布](deployment_and_packaging.md)** | 运维部署与打包 | 支持 CUDA 硬件加速的多阶段 Docker 容器化构建与 Linux Systemd 守护进程单元。 |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
