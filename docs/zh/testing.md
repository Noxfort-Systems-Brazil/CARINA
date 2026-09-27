# 🧪 测试规范与质量验证指南

本文件说明 CARINA 的自动化测试流程、代码覆盖率分析及安全否决确定性验证。

⬅️ [文档中心](../README.md) | 🛡️ [安全机制](safety_and_watchdog.md)

---

## 1. 测试套件执行方式
```bash
# 运行全部 Python 单元测试
./.venv/bin/pytest tests/ -v

# 生成代码覆盖率统计
./.venv/bin/pytest tests/ -v --cov=src

# 执行原生 Go 硬件网关单元测试
cd src_go && go test -v ./...
```

---

## 2. 覆盖范围 (53 个单元测试模块)
全面覆盖 PPO/D3QN 核心决策逻辑、FENIX 自愈机制、Go 硬件网关 IPC 管道、SNMP 协议栈、密码学认证以及 Flet 桌面交互。
