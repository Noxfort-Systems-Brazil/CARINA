# 🏛️ CARINA: 系统架构核心蓝图与多进程并发模型

本规范详细阐述 CARINA 生态系统的底层工程架构：8个操作系统并发微服务进程的解耦设计、深度神经网络拓扑结构、ST-GATv2 Lite 时空图注意力网络、全局顾问 PAE 预测自编码器以及 PostgreSQL 异步增量压缩引擎。

⬅️ [文档中心](../README.md) | 🚦 [硬件驱动](hardware_drivers.md) | 🛡️ [安全机制](safety_and_watchdog.md)

---

## 1. 多进程并发微服务模型
为了绕过 Python 全局解释器锁（GIL）并确保控制决策的亚毫秒级响应，CARINA 采用了由 `carina.py` 与 `src/launcher/process_manager.py` 统筹管理的**多进程微服务并发模型**：
- `CentralController`：实时 gRPC 服务与高频硬件调度。
- `AI_Process`：强化学习策略前向推理与网络优化。
- `Watchdog`：高敏看门狗守护进程（< 500 ms 响应）。
- `DashboardService (SDS)`：前端 Flet 界面通信与 WebSocket 广播。
- `StepDecisionWorker & DatabaseWorker`：无阻塞异步数据持久化。
- `XAI_Worker`：本地大模型与司法审计报告生成。
- `MFD_Worker`：宏观基本图与交通流动力学分析。

---

## 2. 深度强化学习拓扑与加速
- **局部战术层 (PPO-TCN)：** 采用一维膨胀因果卷积提取时间序列特征，执行实时信号相位时长决策。
- **干道协调层 (ST-GATv2 Lite)：** 动态图注意力权重计算，跨交叉口协调主干道“绿波带”。
- **全局顾问层 (PAE 128通道)：** 高容量预测自编码器预测未来交通流状态趋势。
- **Universal AMP 硬件加速：** 基于 NVIDIA TensorCores 全面开启 FP16 自动混合精度，核心模型显存占用压缩至仅约 20 MB。

---

## 3. 增量压缩存储与 Go 硬件网关
- **PostgreSQL 增量存储：** 采用游程编码压缩连续相同状态，将数据库磁盘占用降低 **97.9%**。
- **Go 硬件网关 (`bin/carina-go`)：** 独立二进制进程处理 UDP 161 (SNMP) 与 162 (Traps)，通过系统匿名管道通信，主机无需暴露任何网络端口。
- **FENIX 自动自愈：** 子进程状态监控与阶段边界安全平滑交接。
