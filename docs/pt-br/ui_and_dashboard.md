# 🖥️ Arquitetura de Interface, Planning View e Smart Dashboard Service

Este documento especifica a interface gráfica desktop do CARINA localizada em `ui/`, o processo **Smart Dashboard Service (SDS)** em `src/sds/`, a gestão de bandeja do sistema (Tray) e o mecanismo de instância única.

⬅️ [Central de Documentação](../README.md) | 🏛️ [Arquitetura](architecture.md) | 🚦 [Controladores de Hardware](hardware_drivers.md)

---

## 1. Arquitetura Desacoplada com SDS (`ui/` e `src/sds/`)

Para evitar que a renderização de telas em Flutter/Flet atrase a tomada de decisão em tempo real, a interface é desacoplada do motor de controle através do processo **`DashboardService` (SDS)**:
- Comunicação via filas de memória de sub-milissegundo (`ui_telemetry`).
- Servidor WebSocket local (porta 8080) para clientes web opcionais.

---

## 2. Visão de Planejamento da Malha Semafórica (Planning View)

Localizada em `ui/views/planning_view.py`:
- **Agrupamento Topológico:** Agrupamento de corredores arteriais para coordenação de Onda Verde.
- **Inspetor de Estágios e Fases:** Configuração interativa de tempos de verde mínimo, entreverdes e matrizes de conflito.
- **Exportação e Sincronização:** Exportação direta de planos semafóricos para repositórios de hardware ou planilhas CSV.

---

## 3. Bloqueio de Instância Única (`SingleInstanceLock`)
Utiliza a porta TCP local `42123` para impedir a execução duplicada do sistema, restaurando a janela ativa caso o executável seja acionado novamente.
