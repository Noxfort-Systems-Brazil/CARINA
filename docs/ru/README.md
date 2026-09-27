<div align="center">

<img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="110" />

# CARINA — Комплект технической документации
### Архитектура системы, аппаратная интеграция и безопасность
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Языки / Переводы:** **[🇺🇸 English](../en/README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Главный Хаб](../README.md)**

---

</div>

## Добро пожаловать в официальную документацию CARINA

В данном каталоге представлен полный комплект технической документации на **русском языке** для системы **CARINA** (Cognitive Autonomous Real-time Intersection Network Architecture) — корпоративной распределенной платформы глубокого обучения с подкреплением для адаптивного управления светофорными сетями в реальном времени.

## Содержание руководств

| Документ | Раздел | Основные темы |
|---|---|---|
| 📖 **[Архитектура системы](architecture.md)** | Базовая архитектура | 8 параллельных микросервисов ОС, графовое внимание ST-GATv2 Lite, консультант PAE (128 каналов) и аппаратное ускорение AMP/TensorCores. |
| 🔌 **[Драйверы и шлюз на Go](hardware_drivers.md)** | Аппаратная часть | Промышленный шлюз на Go (`carina-go`), межпроцессный обмен NDJSON через анонимные каналы (без открытых портов), протоколы NTCIP 1202 и UTMC2. |
| 🛡️ **[Безопасность, Watchdog и FENIX](safety_and_watchdog.md)** | Нейро-символическая защита | Символические правила вето (SR-01—SR-05), нейросетевое вето Guardian D3QN от заторов, Watchdog (< 500 мс) и система самовосстановления F.E.N.I.X. |
| ⚡ **[API Synapse HFT и каналы IPC](api_reference.md)** | Высокочастотные интерфейсы | Высокоскоростной gRPC-интерфейс Synapse HFT (порт 50051), 10 буферизованных каналов памяти и полиморфный транспорт телеметрии (MQTT и HTTP). |
| 🗄️ **[База данных и дельта-сжатие](database_and_schemas.md)** | Хранение данных | Асинхронное ядро хранения с RLE-дельта-сжатием в PostgreSQL (**сокращение объема на 97.9%**), компактные перечисления Smallint и 12-Factor `.env`. |
| 🧪 **[Тестирование и валидация](testing.md)** | Контроль качества | Набор тестов Pytest (53 модуля), нативные тесты на Go (`go test`), моки дорожных контроллеров и проверка покрытия. |
| 🔍 **[Объяснимый ИИ (XAI) и SAS](xai_and_sas.md)** | Судебный и технический аудит | Google Captum Integrated Gradients, 5 формальных математических уравнений и генератор отчетов Word (.docx) в строгом соответствии стандартам. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Интеллектуальные транспортные системы • CARINA CORE v1.2.0</i>
</div>
