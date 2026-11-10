# CARINA — Demonstration & Video Recording Suite

Este diretório contém a infraestrutura autocontida para inicialização de instâncias de demonstração e geração automatizada de vídeos de apresentação do **CARINA**.

---

## 📁 Estrutura de Arquivos

```text
demo/
├── README.md               # Esta documentação
├── record.sh               # Pipeline 1-click para gravação completa da CARINA com EVP
├── record_presentation.cjs # Orquestrador Playwright CARINA (1080p @ 60 FPS)
├── record_cco.sh           # Pipeline 1-click para gravação do Videowall CCO
├── record_cco.cjs          # Orquestrador Playwright CCO (1080p @ 60 FPS)
├── demo_launcher.py        # Launcher do servidor Flet CARINA em modo headless/web
├── carina_demo_feed.py     # Simulador de telemetria HFT, dinâmica viária e frota EVP
├── evp_vehicle_simulator.py# Simulador de viaturas de emergência (SAMU, Bombeiros, PM)
├── mock_report_generator.py# Gerador de relatórios e dados sintéticos para MFD e XAI
├── tests/                  # Scripts de teste, depuração e calibração de interface
│   ├── test_coords.cjs
│   ├── test_planning.cjs
│   ├── test_street_click.cjs
│   └── test_tabs_switch.cjs
└── recordings/             # Diretório de saída dos vídeos gerados (ignorado no Git)
    ├── carina_apresentacao.mp4
    ├── carina_cco_apresentacao.mp4
    └── scenes/
```

---

## 🚀 Como Usar

### 1. Gravação Automatizada da Apresentação CARINA (com EVP)
Para iniciar a demonstração, gravar o tour completo com dinâmicas de tráfego, preempção de emergência (EVP), IA e diagnósticos em Full HD (1080p @ 60 FPS):

```bash
./demo/record.sh
```

O vídeo final será gerado em:
`demo/recordings/carina_apresentacao.mp4`

### 2. Gravação Automatizada do Videowall CCO
Para iniciar o Go Web Gateway, o simulador de frota e gravar o tour pelas funcionalidades do Videowall CCO:

```bash
./demo/record_cco.sh
```

O vídeo final será gerado em:
`demo/recordings/carina_cco_apresentacao.mp4`

### 3. Executar Apenas o Servidor de Demonstração (Web)
Caso deseje apenas interagir manualmente com a interface de demonstração no navegador:

```bash
source .venv/bin/activate
python demo/demo_launcher.py
```

Acesse em: `http://127.0.0.1:8550` (CARINA Flet) ou `http://127.0.0.1:2201/cco/` (Videowall CCO)
