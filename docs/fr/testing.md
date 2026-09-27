# 🧪 Directives de Tests et Validation

Ce document décrit les protocoles de tests unitaires, d'intégration et de validation de sécurité de CARINA.

⬅️ [Hub de Documentation](../README.md) | 🛡️ [Sécurité](safety_and_watchdog.md)

---

## 1. Exécution des Suites de Tests
```bash
# Tests unitaires Python
./.venv/bin/pytest tests/ -v

# Rapport de couverture
./.venv/bin/pytest tests/ -v --cov=src

# Tests natifs du démon Go
cd src_go && go test -v ./...
```

---

## 2. Couverture Modulaire (53 Modules Unitaires)
Vérification complète des agents PPO, Guardian et Consultant, des mécanismes d'auto-guérison F.E.N.I.X., de la passerelle Go, des communications SNMP, de la sécurité par mot de passe et de l'interface graphique Flet.
