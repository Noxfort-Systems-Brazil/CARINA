<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — Комплект технической документации
### Архитектура системы, аппаратная интеграция и среда безопасности
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Языки / Переводы:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Главный Хаб](../index.md)**

---

</div>

## Добро пожаловать в официальную техническую документацию

Данный каталог содержит полный комплект официальной технической документации на русском языке для платформы **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — промышленной экосистемы глубокого обучения с подкреплением для адаптивного распределенного управления светофорными сетями городов.

## Каталог технических руководств

| Документ | Тематика | Ключевое содержание |
|---|---|---|
| 📚 **[Главная карта знаний (MOC)](carina_moc.md)** | Обзор и граф знаний | Обзор кодовой базы, архитектурная иерархия каталогов и двунаправленный граф Obsidian. |
| 📖 **[Архитектура системы](architecture.md)** | Базовая архитектура ядра | 8 параллельных микросервисов ОС, единый владелец `CARINA_GATEWAY_ROLE`, ST-GATv2 Lite, iTransformer PAE и QR-D3QN. |
| 🚑 **[Приоритетный пропуск (EVP)](evp_and_preemption.md)** | Приоритет спецтранспорта | Автономные «зелёные коридоры», кинематика по формуле гаверсинусов ($60\text{--}160\text{ м}$), межпроцессная синхронизация и защищённый токенами веб-шлюз (порт 2201). |
| 🔌 **[Драйверы контроллеров и Go Gateway](hardware_drivers.md)** | Полевые контроллеры | Шлюз на Go с единым владельцем (`carina-go`), IPC по пайпам NDJSON, NTCIP 1202 (`.4.1.*`/`.5.1.*`), UTMC2, SNMPv3 USM, замкнутое декодирование фаз и бинарные трапы. |
| 🛡️ **[Архитектура безопасности, Watchdog и FENIX](safety_and_watchdog.md)** | Нейро-символическая безопасность | `PhysicalActionMasker`, символические правила (SR-00—SR-06), калибровка QR-D3QN + Noisy-OR в `CHILD`, Watchdog и замкнутая передача управления F.E.N.I.X. |
| ⚡ **[API Synapse HFT и очереди IPC](api_reference.md)** | Высокочастотный интерфейс | gRPC Synapse HFT (TLS/mTLS и Bearer-аутентификация, порт 50051), 12 ограниченных очередей IPC + 1 потокобезопасный пайп и пиннинговая рассылка CCO. |
| 🗄️ **[Архитектура БД и схемы данных](database_and_schemas.md)** | Хранилище и схемы | Дельта-хранилище PostgreSQL (**сокращение на 97.9%**), `PostgresConnectionPool`, SQLite WAL, SQL `make_interval` и 168-часовое хранение телеметрии EVP. |
| 🧠 **[Нейросетевые исследования и формулы](research_notes.md)** | Математическое моделирование | Унифицированный TCN (`GroupNorm` + `SiLU`), батчинг `torch.vmap`, iTransformer PAE, QR-D3QN + Noisy-OR, ST-GATv2 CTDE и бинарная программа DA SILVA ($\ln 2$). |
| 🚦 **[Светофорные обоснования (MUTCD)](traffic_engineering_warrants.md)** | Организация движения | Алгоритмическая оценка нормативных критериев FHWA/MUTCD для установки светофоров (критерии 1—4: Объем, Задержка, Очередь, Насыщение). |
| 📈 **[MFD и сетевая макроаналитика](mfd_and_analytics.md)** | Макроскопическая физика потоков | Регрессии макроскопической фундаментальной диаграммы (MFD), устранение падения пропускной способности, периметральное дозирование и кэш фильтра инцидентов. |
| 🔍 **[Объяснимый ИИ (XAI) и SAS](xai_and_sas.md)** | Муниципальный аудит и XAI | Интегрированные градиенты Google Captum (кэшированный многоагентный конвейер), 5 формальных уравнений и модуль криминалистического аудита вето Guardian. |
| 📄 **[Генератор аналитических отчетов](report_blocks_and_templates.md)** | Автоматизированная отчетность | Генерация Word (.docx) по стандарту ABNT NBR 14724 с формулами OMML и модулем `ReportNumberFormatter` с `stat`-кэшированием. |
| 🤖 **[Компактные языковые модели (SLM)](slm_and_local_llm.md)** | Автономный приватный ИИ | Локальный инференс Qwen3.5 2B / llama.cpp с сериализацией через `slm_process_lock`, зондированием VRAM через `pynvml` и явным вызовом `unload()`. |
| 🖥️ **[Графический интерфейс и планировщик](ui_and_dashboard.md)** | Фронтенд-архитектура | Десктопный GUI на Flet, веб-интерфейс CCO на React 18 (композитные анимации и вьюпорт rAF), пауза окна `MapAnimator` и пагинированный `AuditLogWidget`. |
| 🗺️ **[Векторный рендеринг карт и теплокарты](rendering_and_heatmaps.md)** | Геопространственная визуализация | LRU-кэш карт SUMO `.net.xml` (`read_sumo_net_cached`), внеэкранный рендеринг `mpl_utils` и асинхронные теплокарты KDE. |
| 🔐 **[Безопасность и аутентификация](security_and_auth.md)** | Контроль доступа | RBAC, блокировка PBKDF2 с солью, gRPC TLS/mTLS и Bearer-аутентификация, fail-closed веб-шлюз с кодом `503` и пиннинг сертификатов SHA-256. |
| 🛠️ **[Руководства разработчика](developer_guides.md)** | Разработка и расширение | Конфигурация 12-Factor `.env` и секция `[SYNAPSE]`, `CARINA_GATEWAY_ROLE`, разделенные протоколы `src/interfaces/` и пользовательские агенты. |
| 🧪 **[Тестирование и контроль качества](testing.md)** | Обеспечение качества | **967 тестов Pytest** (935 модульных, 18 интеграционных, 14 корневых), **46 юнит-тестов Go**, `scripts/pytest_limited.sh` и `tests/memory_guard.py`. |
| 🚀 **[Развертывание и пакетирование](deployment_and_packaging.md)** | Эксплуатация и DevOps | Многоэтапные сборки Docker, службы Systemd, fail-closed веб-шлюз Zero-Trust и развертывание Tailscale Funnel. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
