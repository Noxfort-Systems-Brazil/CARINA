# 🧪 Guía de Pruebas y Aseguramiento de Calidad

Este documento especifica los procedimientos de prueba, cobertura de código y validación determinista de seguridad en CARINA.

⬅️ [Centro de Documentación](../README.md) | 🛡️ [Seguridad y Watchdog](safety_and_watchdog.md)

---

## 1. Ejecución de Pruebas

### 1.1 Pruebas Unitarias en Python (`pytest`)
```bash
./.venv/bin/pytest tests/ -v
```

### 1.2 Medición de Cobertura
```bash
./.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
```

### 1.3 Pruebas Nativas del Gateway Go
```bash
cd src_go && go test -v ./...
```

---

## 2. Catálogo de Pruebas (53 Módulos Unitarios)
La suite cubre agentes de aprendizaje por refuerzo, el subsistema de resiliencia F.E.N.I.X., el puente IPC del gateway en Go, los transportes polimórficos, la seguridad con contraseñas bcrypt, los generadores de informes XAI y la interfaz gráfica Flet.
