# 🗄️ 数据库架构与增量存储关系模式

本文件阐述 CARINA 的非阻塞异步持久化层、PostgreSQL 增量压缩机制以及遵循 12-Factor App 的安全凭证管理。

⬅️ [文档中心](../README.md) | 🏛️ [系统架构](architecture.md)

---

## 1. 异步无阻塞持久化与增量压缩
所有实时数据先进入内存队列缓冲（压入耗时 < 0.001 ms），由后台独立工作进程每 50 条批量写入。连续相同状态通过游程编码压缩，使磁盘空间消耗降低 **97.9%**。

---

## 2. 核心关系表模式
- `step_decisions`：记录各智能体的提议动作、Guardian 安全否决与耗时（采用 1 字节 Smallint 枚举）。
- `synapse_fluid_dynamics`：高频车流动力学遥测指标。
- `hardware_controller_connections`：实体信号机 IP、端口及 SNMP 共同体配置。
- `users`：基于 bcrypt 加盐哈希的用户鉴权与防爆破锁定表。
