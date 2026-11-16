---
tags: [deployment, packaging, docker, debian, systemd]
aliases: [Руководство по развертыванию, Пакетирование, Docker, Systemd]
---

# 🚀 Развертывание и конфигурация системных служб

Данный документ описывает варианты промышленного развертывания платформы CARINA, включая настройку системных служб Systemd, контейнеризацию в Docker и конфигурацию сетевого окружения.

⬅️ Назад в [Главный хаб документации](carina_moc.md) | 🛠️ См. [Руководства разработчика](developer_guides.md) | 🗄️ См. [База данных и схемы](database_and_schemas.md) | 🧪 См. [Тестирование и контроль качества](testing.md) | 🚑 См. [Приоритет спецтранспорта (EVP)](evp_and_preemption.md)

---

## 1. Сетевые порты и спецификация коммуникаций

CARINA координирует локальные конвейеры процессов, дорожные контроллеры и видеостены ситуационных центров с использованием выделенных портов:

| Порт | Протокол | Подсистема / Процесс | Описание |
| :--- | :--- | :--- | :--- |
| **`50051`** | TCP (gRPC) | CentralController (Synapse HFTLink) | Внешний высокочастотный gRPC-сервер с опциональным TLS/mTLS и Bearer-аутентификацией (`CARINA_GRPC_*`). |
| **`8080`** | TCP (WS) | Smart Dashboard Service (SDS) | Сервер WebSocket телеметрии, передающий данные очередей с противодавлением (backpressure) и таймаутами 2.0 с. |
| **`2201`** | TCP (HTTP/HTTPS/SSE) | Веб-шлюз Go (`src_go/web_gateway`) | Настраивается через `CARINA_GATEWAY_PORT`; работает по принципу fail-closed (`503`) до включения `CARINA_GATEWAY_ENABLED=True`; защищает эндпоинты токенами и опциональным TLS. |
| **`8085`** | TCP (HTTP/HTTPS) | Автономный приемник EVP (`src_go/evp_go`) | Слушатель GPS-телеметрии спецтранспорта с поддержкой аутентификации Bearer/`X-EVP-Token` и TLS. |
| **`42123`** | TCP (Local) | SingleInstanceLock (`single_instance.py`) | Сокетный мьютекс ОС для предотвращения дублирования экземпляров приложения; принимает сигнал `RESTORE`. |
| **`161`** | UDP (SNMP) | Контроллеры NTCIP 1202 / UTMC2 | Опрос по SNMPv2c/v3 и удержание фаз, управляемые исключительно процессом `CARINA_GATEWAY_ROLE=owner` (`CentralController`). |
| **`162`** | UDP (Trap) | Слушатель аппаратных прерываний (`traplistener`) | Настраивается через `CARINA_TRAP_PORT`; декодирует бинарные пакеты SNMPv1/v2c/v3 Trap и Inform. |

---

## 2. Сборка базовых подсистем

Перед запуском CARINA в промышленную эксплуатацию необходимо собрать нативные бинарные модули и веб-компоненты:

### 2.1 Компиляция аппаратного и веб-шлюза на Go
Скомпилированный демон на Go обслуживает SNMP-опрос контроллеров, микросекундные команды преемпции EVP и трансляцию потока на видеостены CCO:
```bash
cd src_go
go build -ldflags="-s -w" -o ../bin/carina-go ./cmd/gateway
chmod +x ../bin/carina-go
```

### 2.2 Сборка веб-панели оператора CCO на React
Веб-интерфейс Central Control Operator (CCO) расположен в каталоге [`src_tsx/`](../../src_tsx):
```bash
cd src_tsx
npm install
npm run build
```
Сборщик Vite сохраняет готовый продакшн-бандл в `src_tsx/dist/`, который автоматически отдается веб-шлюзом на Go по адресу `http://localhost:2201/cco/`.

---

## 3. Контейнеризация в Docker (`Dockerfile`)

CARINA включает оптимизированный многоэтапный `Dockerfile` для запуска контейнеров с аппаратным ускорением GPU:

### 3.1 Сборка Docker-образа
```bash
docker build -t carina-core:latest .
```

### 3.2 Запуск контейнера с ускорением GPU и пробросом портов
```bash
docker run -d \
  --name carina_app \
  --gpus all \
  -p 50051:50051 \
  -p 8080:8080 \
  -p 2201:2201 \
  -p 8085:8085 \
  -v /var/log/carina:/app/logs \
  -v /etc/carina:/app/config \
  carina-core:latest
```

---

## 4. Конфигурация системного демона Linux Systemd

Для запуска CARINA в качестве системной службы в Ubuntu/Debian Linux:

Создайте файл `/etc/systemd/system/carina.service`:

```ini
[Unit]
Description=CARINA AI Real-Time Traffic Orchestrator
After=network.target postgresql.service

[Service]
Type=simple
User=carina
WorkingDirectory=/opt/carina
ExecStart=/usr/bin/python3 /opt/carina/carina.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Примените изменения и активируйте службу:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carina
sudo systemctl start carina
```

---

## 5. Развертывание Zero-Trust fail-closed шлюза и Tailscale Funnel

Для распределенных агломерационных сетей без публичных белых статических IP:
1. Сохраняйте `CARINA_GATEWAY_ENABLED=False` (значение по умолчанию в `.env.example` и `config/settings.ini`) до тех пор, пока не будут подготовлены токены авторизации и сертификаты TLS; пока шлюз выключен, веб-шлюз Go отдает `503 Service Unavailable` на эндпоинтах CCO/EVP.
2. Создайте ключ Tailscale Auth Key с правами `funnel` в панели администрирования Tailscale и надежные Bearer-токены для EVP, CCO и Synapse gRPC.
3. Укажите параметры в файле `.env`:
   ```bash
   CARINA_GATEWAY_ENABLED=True
   CARINA_GATEWAY_PORT=2201
   CARINA_TRAP_PORT=162
   CARINA_EVP_AUTH_TOKEN=<strong-evp-token>
   CARINA_CCO_AUTH_TOKEN=<strong-cco-token>
   CARINA_CCO_ALLOWED_ORIGIN=https://<node-name>.<tailnet>.ts.net
   CARINA_GATEWAY_TLS_CERT=/etc/carina/certs/gateway.crt
   CARINA_GATEWAY_TLS_KEY=/etc/carina/certs/gateway.key
   CARINA_GRPC_AUTH_TOKEN=<strong-grpc-token>
   CARINA_GRPC_TLS_ENABLED=True
   CARINA_OUTPUT_DIR=/var/lib/carina
   CARINA_CONFIG_DIR=/etc/carina
   CARINA_TAILSCALE_AUTH_KEY=tskey-auth-kXXXXX-XXXXXXXX
   ```
4. `CentralController` запускается в роли `CARINA_GATEWAY_ROLE=owner` (передавая токены и настройки TLS бинарнику `bin/carina-go`), тогда как воркеры UI/AI/SDS работают в роли `remote`. Модуль [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go) регистрирует узел и поднимает HTTPS Funnel по адресу `https://<node-name>.<tailnet>.ts.net:2201`.

---

## 6. Пакетирование и герметичная дистрибуция Debian (`.deb`)

CARINA предоставляет полностью контейнеризированный многоэтапный герметичный сборщик на базе Docker и Docker Buildx ([`scripts/build_deb.sh`](../../scripts/build_deb.sh) и [`packaging/Dockerfile.build`](../../packaging/Dockerfile.build)):

- **Этап 1 (Фронтенд):** Компиляция веб-карты CCO на React/TypeScript в продакшн-бандлы (`node:20-bookworm-slim`).
- **Этап 2 (Шлюз на Go):** Компиляция исполняемого файла `bin/carina-go` без внешних зависимостей CGO (`golang:1.24-alpine`).
- **Этап 3 (Python Virtualenv):** Настройка изолированного окружения в `/opt/carina/venv` с Python 3.12, процессорными оптимизациями PyTorch и полным набором зависимостей (`ubuntu:24.04`).
- **Этап 4 (Сборщик Debian):** Упаковка бинарных файлов, конфигураций, системного сервиса (`carina.service`) и ярлыков рабочего стола в самодостаточный Debian-пакет (`dist/carina_1.0.0_amd64.deb`).

### Сборка пакета
Для генерации чистого и воспроизводимого установочного пакета:
```bash
./scripts/build_deb.sh
```

### Установка пакета
```bash
sudo dpkg -i dist/carina_1.0.0_amd64.deb
sudo apt-get install -f  # Установка системных зависимостей (SUMO, libgl1 и т.д.)
```
Инсталлятор автоматически настраивает директорию `/opt/carina`, регистрирует службу `carina` в systemd и создает ссылку на консольный запуск `/usr/local/bin/carina`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Инженерия Интеллектуальной Мобильности • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Лицензия AGPLv3 или более поздней версии (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
