---
tags: [renderizacao, mapas-de-calor, mapas, sumo, visualizacao, graficos]
aliases: [Motor de Renderização, Mapas de Calor, Gerador de Mapas, Visualização em Canvas]
---

# 🗺️ Motor de Renderização de Mapas e Mapas de Calor Assíncronos

Este documento especifica o subsistema de renderização geoespacial e visualização de tráfego do CARINA localizado em `src/rendering/`. Ele detalha a geração vetorial estática a partir de arquivos de malha viária do SUMO (`.net.xml`), projeções espaciais de coordenadas e interpolação assíncrona de mapas de calor em tempo real.

⬅️ [Central de Documentação](README.md) | 🖥️ [Interface Desktop e Dashboard](ui_and_dashboard.md) | 📈 [Diagrama Fundamental (MFD)](mfd_and_analytics.md)

---

## 1. Arquitetura do Subsistema

O CARINA fornece visualização geoespacial nativa sem depender de provedores externos de mapas na nuvem ou serviços proprietários de satélite. O subsistema opera 100% offline em redes isoladas:

```text
 Rede Viária do SUMO (`.net.xml`) / Telemetria
                      │
                      ▼
        ┌───────────────────────────┐
        │  map_coordinate_generator │ (Converte UTM/Cartesiano -> Pixels de Tela)
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│   static_map_renderer  │  │ async_heatmap_renderer │
│(Faixas, Nós, Semáforos)│  │(Densidade KDE e Atraso)│
└───────────┬────────────┘  └───────────┬────────────┘
            │                           │
            └─────────────┬─────────────┘
                          ▼
            Superfície Nativa Canvas Flet
               (`LiveCanvasMapWidget`)
```

---

## 2. Módulos Centrais em `src/rendering/`

### 2.1 Transformação de Coordenadas (`map_coordinate_generator.py`)
Localizado em `src/rendering/map_coordinate_generator.py`:
- Converte projeções 2D do SUMO $(x, y)$ em coordenadas de viewport $(u, v)$ no canvas gráfico.
- Suporta translação suave (*pan*), aproximação dinâmica (*pinch-to-zoom*) e auto-centralização calculada pela bounding box das interseções ativas.
- Preserva a proporção métrica em telas widescreen e monitores industriais.

### 2.2 Renderizador Vetorial Estático (`static_map_renderer.py`) & Cache LRU de Rede SUMO (`sumo_net_cache.py`)
Localizado em [`src/rendering/static_map_renderer.py`](../../src/rendering/static_map_renderer.py) e [`src/utils/sumo_net_cache.py`](../../src/utils/sumo_net_cache.py):
- Realiza o parse da geometria das faixas do arquivo `.net.xml`, conexões internas e polígonos de cruzamento através de [`read_sumo_net_cached()`](../../src/utils/sumo_net_cache.py) (cache LRU thread-safe de até 8 entradas indexado por caminho, `mtime_ns`, tamanho, `with_programs` e `with_internal`).
- Desenha vias arteriais com divisores de pista, setas direcionais e ícones de focos semafóricos.
- Utiliza cache em memória de caminhos vetoriais rasterizados para evitar recálculos desnecessários de CPU.

### 2.3 Renderizador Assíncrono de Mapas de Calor (`async_heatmap_renderer.py`) & Matplotlib Offscreen (`mpl_utils.py`)
Localizado em [`src/rendering/async_heatmap_renderer.py`](../../src/rendering/async_heatmap_renderer.py) e [`src/rendering/mpl_utils.py`](../../src/rendering/mpl_utils.py):
- Utiliza **Estimativa de Densidade por Kernel (KDE)** para interpolar mapas de calor espaciais contínuos a partir de métricas discretas de aproximação:
  - **Densidade Veicular:** Acúmulo de veículos por quilômetro quadrado.
  - **Tempo de Espera e Atraso:** Destaca gargalos e estrangulamentos viários.
  - **Risco de Spillback:** Visualiza ondas de congestionamento projetadas pelo Guardião.
- Executa a convolução gaussiana e interpolações matriciais em threads assíncronas em segundo plano, e renderiza gráficos através de instâncias offscreen isoladas de `Figure` + `FigureCanvasAgg` (`create_offscreen_figure` / `close_offscreen_figure`) em vez do estado global do `pyplot`, prevenindo vazamentos de memória e contenção na thread da GUI.

---

## 3. Configuração e Gradientes de Cor

Pesos e gradientes de calor são configurados em `config/settings.ini`:

```ini
[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_flow = 1.0
saturation_threshold = 0.85
lane_aggregation_strategy = max
heatmap_strategy = combined
heatmap_saturation = 1.0
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Computação Gráfica e Cartografia • CARINA CORE v1.2.0</i>
</div>
