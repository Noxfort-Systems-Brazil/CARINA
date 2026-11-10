---
tags: [ui, flet, dashboard, frontend, sds, planejamento, widgets]
aliases: [Arquitetura de UI, Serviço Dashboard, Frontend Flet, Visão de Planejamento]
---

# 🖥️ Arquitetura de UI, Visão de Planejamento & Serviço Smart Dashboard

Este documento especifica a interface de usuário desktop nativa do CARINA localizada em [`ui/`](../../ui), o **Smart Dashboard Service (SDS)** em [`src/sds/`](../../src/sds), o **Gerenciador de Bandeja de Sistema (Tray)**, a aplicação web da **Central de Controle Operacional (CCO)** e o sistema de bloqueio de instância única.

⬅️ [Central de Documentação](carina_moc.md) | 🗺️ [Renderização & Mapas de Calor](rendering_and_heatmaps.md) | 🔍 [IA Explicável & SAS](xai_and_sas.md) | 🚑 [Preempção de Emergência (EVP)](evp_and_preemption.md)

---

## 1. Arquitetura Desktop Desacoplada (`ui/` & `src/sds/`)

Para impedir que renderizações pesadas de interface gráfica ou lentidões de sockets no navegador causem perda de quadros no controle de tráfego em tempo real, o CARINA desacopla totalmente seu frontend no processo dedicado **`DashboardService` (SDS)** ([`run_sds_worker`](../../src/sds/dashboard_worker.py)):

```text
CentralController (gRPC) ──> [Fila sds] ──> DashboardService (SDS) ──> [Fila ui] ──> UI Flet (Thread Principal)
                                                   │
                                                   └──> Servidor de Telemetria WebSocket (porta 8080)
```

---

## 2. Arquitetura Flet Real & Hierarquia de Visões

O frontend desktop é construído utilizando **[Flet](https://flet.dev/)** (motor Python + Flutter) localizado em [`ui/`](../../ui):

```text
ui/
├── main_ui.py                      # Bootstrap principal da aplicação Flet & inicialização da janela
│
├── views/                          # Telas e Visões Principais da Aplicação
│   ├── dashboard_view.py           # Monitoramento de tráfego em tempo real & tela interativa do mapa
│   ├── planning_view.py            # Planejamento topológico da malha, tempos de fase & agrupamentos
│   ├── diagnostics_view.py         # Métricas de latência IPC, consumo de memória & monitores de processos
│   ├── system_status_view.py       # Estado dos microsserviços ativos & status dos controladores de campo
│   ├── settings_view.py            # Configuração do sistema & editor de endpoints IP de controladores
│   └── error_view.py               # Captura global de erros & tela diagnóstica de exceções
│
├── cards/                          # Cartões Modulares de Configuração & Inspeção (Padrão OCP)
│   ├── evp_fleet_connection_card.py    # Cadastro de viaturas de emergência & RFID/transponders
│   ├── evp_safety_parameters_card.py  # Portais de distância de preempção, watchdog de dwell & entreverdes
│   ├── remote_gateway_card.py          # Ativação do Go Web Gateway, porta 2201 & status Tailscale
│   ├── account_settings_card.py        # Perfil de operador, papéis de acesso (RBAC) & credenciais
│   ├── database_settings_card.py       # Seleção de banco de dados (SQLite/PostgreSQL) & migrações
│   ├── hardware_connection_card.py     # Pool de conexões de controladores de campo NTCIP 1202 & UTMC
│   ├── piloting_school_card.py         # Ritmo autônomo de PBT & limiares de graduação de RL
│   ├── reward_weights_card.py          # Balanceamento de recompensas (espera, pressão, fila e velocidade)
│   ├── traffic_rules_card.py           # Restrições de verde mínimo, entreverde amarelo & vermelho total
│   ├── yellow_schedule_card.py         # Agendamentos de amarelo intermitente noturno autônomo
│   ├── monitor_settings_card.py        # Telemetria externa via broker MQTT / webhook HTTP
│   ├── advanced_system_card.py         # Parâmetros de Watchdog, tamanhos de buffer IPC & heartbeats
│   ├── advanced_dqn_card.py            # Capacidade do replay buffer DQN, sincronização do target e epsilon
│   └── advanced_ppo_card.py            # Razão de corte PPO (clip), coeficientes de entropia e perda de valor
│
├── widgets/                        # Componentes Gráficos Modulares Especializados
│   ├── live_canvas_map_widget.py   # Tela vetorial de alto desempenho renderizando vias e semáforos
│   ├── evp_vehicle_marker.py       # Marcador vetorial customizado para viaturas (formas e sirenes)
│   ├── evp_vehicle_card.py         # Cartão flutuante exibindo GPS em tempo real, velocidade e ETA
│   ├── planning_control_panel_widget.py # Painéis de controle de planejamento, fases e nós
│   ├── mfd_viewer_widget.py        # Plotador em tempo real da curva do Diagrama Fundamental Macroscópico
│   ├── xai_viewer_widget.py        # Gráficos de atribuição de características neurais via Captum
│   ├── street_info_widget.py       # Leituras de velocidade por faixa, taxa de ocupação e extensão de filas
│   ├── traffic_light_widget.py     # Animações de focos semafóricos em tempo real (Vermelho, Amarelo, Verde)
│   ├── audit_log_widget.py         # Tabela de inspeção forense de vetos de segurança do Guardian
│   └── global_controls_widget.py   # Controles de Início, Pausa, Passo a Passo & Liberação de Emergência
│
├── renderers/                      # Desenho Vetorial & Sincronização Visual
│   ├── map_drawer.py               # Rasterizador de geometria vetorial de faixas e cruzamentos
│   ├── planning_map_renderer.py    # Motor de layout visual para nós da topologia
│   └── map_visual_syncer.py        # Sincronizador de animações fluidas a 60 FPS
│
└── locales/                        # Dicionários de Internacionalização (i18n)
    ├── pt_br.json                  # Português (Brasil) - Padrão
    ├── en_us.json                  # Inglês (Estados Unidos)
    ├── es_es.json                  # Espanhol
    ├── fr_fr.json                  # Francês
    ├── ru_ru.json                  # Russo
    └── zh_cn.json                  # Chinês Simplificado
```

---

## 3. Visão de Planejamento & Editor de Topologia de Rede

A **Visão de Planejamento** ([`ui/views/planning_view.py`](../../ui/views/planning_view.py)) permite que engenheiros de tráfego municipais inspecionem e configurem interativamente as redes viárias físicas:
- **Agrupamento Topológico:** Agrupar cruzamentos em corredores arteriais coordenados (Ondas Verdes).
- **Inspetor de Fases e Estágios:** Inspecionar restrições de verde mínimo, entreverdes de amarelo e tempos de limpeza de vermelho total.
- **Exportação de Planos:** Exportar planos semafóricos modificados diretamente para repositórios de controladores ou matrizes em CSV.

Para detalhes sobre renderização vetorial de mapas, consulte [Renderização & Mapas de Calor](rendering_and_heatmaps.md).

---

## 4. Bandeja do Sistema & Trava de Instância Única (`SingleInstanceLock`)

O CARINA opera continuamente em segundo plano com um ícone nativo na bandeja de sistema (System Tray):

### 4.1 Gerenciamento de Bandeja ([`UITrayManager`](../../src/launcher/ui_tray_manager.py))
- **Ações da Bandeja:** Minimizar para Bandeja, Abrir Painel, Ver Logs em Tempo Real, Reiniciar Serviços, Desligamento Seguro.
- **Notificações do Sistema:** Emite alertas nativos do SO quando o Watchdog detecta anomalias de processos ou quando o Guardian Agent emite um veto de segurança.

### 4.2 Trava de Instância Única ([`SingleInstanceLock`](../../src/launcher/single_instance.py))
- **Porta:** `42123`
- Caso um operador tente abrir uma segunda instância do CARINA:
  1. O novo processo tenta vincular a porta TCP `42123`.
  2. Ao falhar, ele envia o sinal `RESTORE` via socket TCP local para a instância primária.
  3. A instância primária traz a janela do Flet para o primeiro plano da área de trabalho, e o segundo processo se encerra de forma limpa.

---

## 5. Arquitetura Modular de Cartões de Configuração (`ui/cards/`)

A tela de configurações do CARINA ([`ui/views/settings_view.py`](../../ui/views/settings_view.py)) implementa o princípio Aberto/Fechado (OCP) estruturado pelo [`SettingsConfigurator`](../../ui/builders/settings_configurator.py):

| Cartão Modular | Descrição | Modos Automático / Manual |
| :--- | :--- | :--- |
| **`EVPFleetConnectionCard`** | Registro de viaturas de emergência e transponders RFID | • Classificação por corporação (Polícia, SAMU, Bombeiros)<br>• Autorização de placas & lista de bloqueio |
| **`EVPSafetyParametersCard`** | Cinemática de preempção, gates e tempos de segurança | • Gate de aproximação ($60\text{--}160\text{ m}$)<br>• Limiar de saída ($\le 15\text{ m}$)<br>• Watchdog de dwell ($45\text{ s}$)<br>• Entreverdes regulamentares |
| **`RemoteGatewayCard`** | Gerenciamento do Gateway Go e malha Tailscale | • Ativação do daemon na porta 2201<br>• Status do Tailscale Funnel & URL pública |
| **`AccountSettingsCard`** | Autenticação de operadores e perfis RBAC | • Atribuição de funções (Operador, Superuser)<br>• Validação de senhas e segurança |
| **`DatabaseSettingsCard`** | Configuração de armazenamento SQLite e PostgreSQL | • Seletor de motor de banco & pool de conexões<br>• Teste de conexão & migração de esquemas |
| **`PilotingSchoolCard`** | Ritmo de maturidade e regras de promoção | • Ritmo dinâmico por nós da malha<br>• Margem de graduação fluida ($\delta^*$) |
| **`RewardWeightsCard`** | Pesos de otimização de RL (Espera vs Fluxo) | • Balanceamento físico automático (tempo livre HCM $\tau$)<br>• Sobrescrita manual de pesos |
| **`YellowScheduleCard`** | Agendamentos de amarelo intermitente noturno | • Agendador de janelas temporais (HH:MM)<br>• Aplicação seletiva ou em toda a malha |
| **`AdvancedSystemCard`** | Parâmetros de PBT e Watchdog em nível de sistema | • Percentil de exploração do PBT<br>• Intervalos de tolerância do Watchdog |
| **`AdvancedDQNCard`** | Hiperparâmetros da rede Deep Q-Network | • Capacidade de replay buffer, sincronismo de target, $\epsilon$-decay |
| **`AdvancedPPOCard`** | Hiperparâmetros do Proximal Policy Optimization | • Razão de corte ($\epsilon=0.2$), coeficiente de entropia, perda de valor |
| **`TrafficRulesCard`** | Restrições estatutárias de tempos semafóricos | • Verde mínimo, entreverde amarelo, vermelho total |
| **`HardwareConnectionCard`** | Controladores físicos de rua (NTCIP / UTMC) | • Endpoints IP, credenciais SNMP & teste de fail-safe |
| **`MonitorSettingsCard`** | Telemetria externa e transmissão de incidentes | • Endpoints de Broker MQTT / Webhooks HTTP |

---

## 6. Marcadores Vetoriais de EVP & Inspetor Flutuante (`ui/widgets/`)

Para a operação desktop, o CARINA renderiza viaturas em atendimento de emergência em tempo real diretamente sobre a tela de simulação:

- **`EVPVehicleMarker` ([`ui/widgets/evp_vehicle_marker.py`](../../ui/widgets/evp_vehicle_marker.py)):**
  - **Ícones por Corporação:** Renderiza geometrias distintas para cada tipo de viatura:
    - *SAMU / Ambulância:* Triângulo Equilátero ($\Delta$, Branco `#FFFFFF` / Alerta Vermelho `#E53935`).
    - *Corpo de Bombeiros:* Quadrado ($\square$, Laranja `#FF9800`/`#FF8C00` / Alerta Vermelho Fogo `#FF3D00`).
    - *Polícia Militar / Civil:* Círculo ($\bigcirc$, Azul Escuro `#1E3A8A` / Alerta Azul Real `#2563EB`).
  - **Animação de Sirene:** Quando `siren_active=True`, pulsa anéis estroboscópicos concêntricos a $2,5\text{ Hz}$ na tela, alertando visualmente os operadores.
  - **Orientação Dinâmica (Heading):** Rotaciona a representação gráfica do veículo acompanhando o ângulo azimute do GPS em tempo real.

- **`EVPVehicleCard` ([`ui/widgets/evp_vehicle_card.py`](../../ui/widgets/evp_vehicle_card.py)):**
  - Cartão HUD flutuante exibindo indicativo da viatura, velocidade atual ($\text{km/h}$), estado da sirene, distância até a linha de retenção ($\text{m}$) e status da preempção (`APPROACHING`, `HOLD_ACTIVE`, `CLEARED`).

---

## 7. Central de Controle Operacional (CCO) Web & Mobile (`src_tsx/src_cco`)

Além da interface desktop em Flet, o CARINA conta com uma plataforma web moderna da **Central de Controle Operacional (CCO)** desenvolvida em **React 18**, **TypeScript**, **Tailwind CSS** e **Vite** em [`src_tsx/src_cco/`](../../src_tsx/src_cco). Sua arquitetura segue rigorosamente os princípios da **Clean Architecture**:

```text
src_tsx/src_cco/
├── domain/                         # Entidades Puras de Domínio, Modelos & Serviços de Negócio
│   ├── models/                     # Entidades Centrais de Negócio
│   │   ├── Topology.ts             # Interfaces de MapTopology, Node, Edge, Bounds
│   │   ├── CongestionLevel.ts      # Value Object resolvendo níveis de retenção e cores
│   │   ├── EmergencyVehicle.ts     # Modelo de estado de telemetria e preempção (SAMU, Bombeiros, Polícia)
│   │   └── TrafficLight.ts         # Modelos de focos semafóricos, estados ativos e cronômetros
│   ├── services/                   # Serviços Puros de Cartografia e Geometria
│   │   ├── MapProjectionService.ts # Projeção ortográfica 2D isotrópica & cálculo de aspecto SVG
│   │   ├── GeoProjectionService.ts # Conversão de GPS WGS84 para coordenadas cartesianas do SUMO
│   │   └── StreetTopologyGrouperService.ts # Agrupamento de vias & geração de caminhos de mapas de calor
│   └── contracts/                  # Interfaces de Fronteira (Inversão de Dependência - DIP)
│       ├── ITopologyRepository.ts  # Contrato para busca da geometria da malha
│       └── ICcoStreamService.ts    # Interface de streaming de eventos em tempo real & conexão
│
├── application/                    # Casos de Uso da Aplicação & Orquestradores
│   └── usecases/
│       ├── LoadTopologyUseCase.ts          # Carregamento e cache da geometria da rede
│       ├── ManageEmergencyFleetUseCase.ts   # Categorização de frotas & cálculo de alertas ativos
│       └── ProcessTelemetryUseCase.ts      # Desempacotamento de payloads SSE em estados de domínio
│
├── infrastructure/                 # Adaptadores Externos, APIs & Gateways
│   ├── api/
│   │   └── HttpTopologyRepository.ts       # Implementação HTTP de busca de topologia
│   ├── stream/
│   │   └── SseCcoStreamService.ts          # Cliente SSE (/cco/stream) com reconexão automática
│   └── adapters/
│       └── EChartsOptionAdapter.ts         # Adaptador convertendo modelos de domínio em opções ECharts
│
└── presentation/                   # Interface Reativa, Hooks, Componentes & Temas
    ├── context/
    │   └── ThemeContext.tsx                # Alternador de tema operacional (☀️ Claro / 🌙 Escuro) com localStorage
    ├── utils/
    │   └── haptics.ts                      # Resposta tátil por vibração em dispositivos móveis
    ├── hooks/
    │   ├── useCcoViewModel.ts              # View-Model raiz orquestrando casos de uso, stream SSE e estado
    │   ├── useCcoMapLayers.ts              # Cálculo memoizado de camadas (ruas, nós, semáforos)
    │   └── useMapViewport.ts               # Gestos de pan, zoom, pinch e animações fluidas flyTo
    ├── components/
    │   ├── CcoHeader.tsx                   # Barra responsiva com distintivos de frota, busca, tema e tela cheia
    │   ├── CcoMap.tsx                      # Mapa vetorial SVG de alto desempenho com navegação isotrópica
    │   ├── EvpAlertToast.tsx               # Notificação retrátil de alerta de emergência (micro-pill no celular)
    │   └── map/
    │       ├── InspectionBottomSheet.tsx   # Painel inferior ergonômico no celular & HUD flutuante no desktop
    │       ├── QuickSearchModal.tsx        # Busca instantânea & centralização automática (flyTo)
    │       ├── MapScaleBar.tsx             # Barra de escala métrica dinâmica (m/km) calibrada com o SUMO
    │       ├── MapRoadsLayer.tsx           # Rasterizador de faixas viárias & mapa de calor de retenção
    │       ├── MapIntersectionsLayer.tsx   # Nós de cruzamento interativos com hit-box de toque
    │       ├── MapTrafficLightsLayer.tsx   # Focos semafóricos com brilho ativo e diagnóstico
    │       ├── MapEmergencyVehiclesLayer.tsx # Marcadores de viaturas, rotação de azimute & auras de sirene
    │       ├── MapGlowFilters.tsx          # Filtros SVG de brilho neon para semáforos e alertas
    │       ├── MapLegend.tsx               # Legenda retrátil de retenção e glifos operacionais
    │       └── MapZoomControls.tsx         # Controles de zoom isotrópico e recentralização de câmera
    ├── styles/
    │   ├── flet_color_palette.json         # Sincronização exata de cores com a paleta do Flet desktop
    │   └── index.css                       # Diretivas Tailwind e travas de rolagem de viewport
    ├── App.tsx                             # Componente raiz com ThemeProvider e modais
    └── main.tsx                            # Ponto de entrada React DOM
```

---

## 8. Capacidades de UI/UX & Ergonomia do CCO

O frontend do CCO foi projetado para prover excelência operacional em videowalls 4K de salas de controle ou em smartphones na rua:

1. **Painel Inferior Ergonômico (`InspectionBottomSheet.tsx`):**
   - Em telas móveis (`< 768px`), o painel de inspeção se acopla na base da tela com suporte a gestos de arrasto para fechar.
   - Em estações desktop (`>= 768px`), as informações flutuam em um HUD compacto lateral.
   - Fornece diagnósticos completos em tempo real para:
     - **Viaturas de Emergência:** Indicativo, velocidade ($\text{km/h}$), azimute ($^\circ$), estado da sirene e cruzamento de destino.
     - **Semáforos:** ID do controlador, fase ativa, lâmpadas virtuais (Verde, Amarelo, Vermelho), coordenadas e supervisão Fenix.
     - **Cruzamentos & Vias:** Nós físicos, nome da via, percentual de saturação ($0\text{--}100\%$) e classificação de escoamento.

2. **Temas Operacionais Duplos (☀️ Diurno / 🌙 Noturno):**
   - **Modo Diurno Cartográfico (`#F7F7F7`):** Fundo claro de alto contraste otimizado para operações de campo sob luz solar.
   - **Modo Videowall Noturno (`#020617`):** Paleta escura profunda reduzindo a fadiga visual dos operadores em salas de controle com pouca iluminação.
   - Alternância instantânea no cabeçalho e persistência automática no `localStorage`.

3. **Busca Rápida com Paleta de Comandos & Centralização Focada (`QuickSearchModal.tsx` & `flyTo`):**
   - Acessível pelo botão de busca ou atalhos globais de teclado (`Ctrl+K` ou `/`).
   - Indexação instantânea de viaturas, semáforos, cruzamentos e nomes de ruas.
   - Selecionar qualquer item dispara uma transição animada de câmera (`flyTo`) com interpolação cúbica suave, centralizando o elemento e abrindo sua ficha técnica.

4. **Barra de Escala Métrica Dinâmica (`MapScaleBar.tsx`):**
   - Escala métrica gráfica (ex: `|—— 100 m ——|`) que se recalibra em tempo real conforme o nível de zoom aplicado.

5. **Filtros Interativos de Frota:**
   - Os emblemas no cabeçalho para **SAMU**, **Bombeiros** e **Polícia** atuam como filtros rápidos. Clicar em uma corporação destaca suas viaturas no mapa e atenua os demais veículos.

6. **Modo Imersivo de Tela Cheia & Resposta Tátil Móvel:**
   - Botão de tela cheia que maximiza a área útil do videowall.
   - Micro-vibrações táteis (`navigator.vibrate`) que confirmam toques em semáforos, viaturas e botões em dispositivos compatíveis.

---

## 9. Entrega pelo Go Web Gateway & Conectividade Remota

O CCO web é servido pelo **Gateway Go de Alto Desempenho** ([`src_go/web_gateway/`](../../src_go/web_gateway)) operando na porta `2201`:
- **Entrega de Artefatos Estáticos:** Serve o pacote compilado do React em `/cco/` com compressão gzip e cabeçalhos de cache otimizados.
- **Transmissão SSE Sub-50ms:** Endpoint `/cco/stream` distribuindo mudanças de estágio, congestionamento e cinemática de viaturas sem overhead de polling.
- **Malha Segura Tailscale:** Integração com Tailscale Funnel para acesso externo seguro sem necessidade de portas abertas em roteadores de borda.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Engenharia de Mobilidade Inteligente • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
