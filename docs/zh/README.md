<div align="center">

<img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="110" />

# CARINA — 官方技术文档套件
### 系统核心架构、硬件集成与神经符号安全机制
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **语言 / Translations:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](README.md)** • **[📚 文档中心](../README.md)**

---

</div>

## 欢迎访问 CARINA 官方技术文档中心

本目录包含 **CARINA**（认知自主实时路口网络架构，Cognitive Autonomous Real-time Intersection Network Architecture）的完整**简体中文**技术文档库。CARINA 是由 Noxfort Systems 开发的高性能分布式深度强化学习平台，专为城市交通信号灯网络的毫秒级实时自适应控制而设计。

## 专业技术指南目录

| 文档 | 领域与范围 | 核心内容 |
|---|---|---|
| 📖 **[系统架构核心设计](architecture.md)** | 系统蓝图 | 8个操作系统并发微服务、ST-GATv2 Lite 时空图注意力网络、全局顾问 PAE（128通道）以及 Universal AMP 硬件加速。 |
| 🔌 **[交通机硬件驱动与 Go 网关](hardware_drivers.md)** | 现场硬件集成 | 工业级编译型 Go 硬件网关 (`carina-go`)、零网络端口匿名管道 NDJSON IPC、NTCIP 1202、UTMC2 协议与原子级故障安全回退。 |
| 🛡️ **[安全机制、看门狗与 FENIX 自愈](safety_and_watchdog.md)** | 神经符号双重安全 | 不可违背的物理符号否决规则 (SR-01 至 SR-05)、D3QN 溢出拥堵神经否决、实时看门狗 (< 500 ms) 与 F.E.N.I.X. 自愈子系统。 |
| ⚡ **[Synapse HFT API 与 IPC 队列](api_reference.md)** | 高频通信规范 | 亚毫秒级 Synapse HFT gRPC 接口 (端口 50051)、10个进程间共享内存队列通道以及多态外部遥测传输 (MQTT 与 HTTP/REST)。 |
| 🗄️ **[数据库架构与增量压缩存储](database_and_schemas.md)** | 持久化与关系模式 | 基于游程编码的 PostgreSQL 异步增量压缩存储引擎（**磁盘占用缩减 97.9%**）、1字节 Smallint 枚举与 12-Factor `.env`。 |
| 🧪 **[测试规范与质量验证](testing.md)** | 质量保证与测试 | 包含 53 个单元测试模块的 Pytest 测试套件、原生 Go 单元测试 (`go test`)、Guardian 安全模拟与覆盖率报告。 |
| 🔍 **[可解释人工智能 (XAI) 与司法审计](xai_and_sas.md)** | 市政合规性 | 谷歌 Captum 积分梯度算法、5个正式数学公式以及符合国际市政工程审计标准的 Word (.docx) 报表自动生成引擎。 |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通工程与移动性科技 • CARINA CORE v1.2.0</i>
</div>
