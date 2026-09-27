# ⚡ Synapse HFT API 与进程间通信 (IPC) 队列规范

本文件规定了 CARINA 的高频 gRPC 通信接口及多进程共享内存通道。

⬅️ [文档中心](../README.md) | 🏛️ [系统架构](architecture.md)

---

## 1. Synapse HFT gRPC 服务 (`proto/synapse_hft.proto`)
- **默认监听端口：** `50051` (TCP / HTTP2)。
- **核心 RPC 方法：**
  - `Ping`：亚毫秒级保活健康探测。
  - `LoadScenario`：下发路网几何拓扑结构。
  - `SystemControl`：系统运行状态指令 (`START`, `PAUSE`, `STOP`, `RESET`)。
  - `StreamTraffic`：高频实时路网状态流（车道占有率、平均车速与排队长度）。

---

## 2. 进程间共享内存队列 (IPC)
通过 `ProcessManager` 创建的 10 个独立内存队列彻底解耦 AI 前向推理、GUI 前端、数据库存储和系统监测。
