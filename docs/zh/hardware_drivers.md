# 🚦 交通机硬件驱动与 Go 硬件网关

本文件详细说明 CARINA 与现场实体信号机（Econolite、西门子 Siemens、Peek、SWARCO、Yunex 等）的底层网络通信架构。

⬅️ [文档中心](../README.md) | 🏛️ [系统架构](architecture.md) | 🛡️ [安全机制](safety_and_watchdog.md)

---

## 1. 独立 Go 硬件网关 (`bin/carina-go`)
为彻底杜绝 Python 垃圾回收与 GIL 造成的通信抖动，CARINA 将所有信号机网络 I/O（UDP 161 与 162 端口）移至专用的 Go 语言编译进程：
- **匿名管道 IPC：** Python 核心与 Go 网关间采用标准输入输出流 (`stdin`/`stdout`) 进行行分隔 JSON（NDJSON）交换，**宿主机对外开放网络端口为零**。
- **原子级故障安全：** 一旦 Python AI 进程意外崩溃或关闭，操作系统内核即刻关闭管道 (`EOF`)，Go 网关在数微秒内捕获该事件并通过 SNMP 立即释放所有相位保持命令，使物理机柜平稳退回本地固定配时。

---

## 2. 通信协议标准
- **NTCIP 1202 标准：** 支持相位保持 (`ascPhaseHold`)、强制切换 (`ascPhaseForceOff`) 和虚拟车辆检测器调用。
- **UTMC / UTMC2 英国标准：** 支持阶段请求 (Stage 1..8) 与应答解析。
- **透明 Python 代理 (`GoTrafficDriverProxy`)：** 完全遵循里氏替换原则，对上层决策透明。
