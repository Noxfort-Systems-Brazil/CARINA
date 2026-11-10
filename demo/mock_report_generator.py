# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import io
import json
import logging
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate_mfd_plot_base64() -> str:
    """Generates a high-resolution dark-themed Macroscopic Fundamental Diagram plot."""
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor="#0d1117", dpi=150)
    ax.set_facecolor("#161b22")

    # Synthetic MFD curve: Flow Q vs Density k
    k = np.linspace(0, 100, 200)
    # Quadratic parabolic fit with realistic skew
    q = 3450 * (4 * (k / 100) * (1 - 0.7 * (k / 100))) / (4 * 0.48 * (1 - 0.7 * 0.48))
    q = np.maximum(q, 0)

    # Shaded regions
    ax.axvspan(0, 48, color="#00e676", alpha=0.08, label="Regime Subcrítico (Fluxo Livre)")
    ax.axvspan(48, 100, color="#ff5252", alpha=0.08, label="Regime Hipercrítico (Congestionamento)")

    # Scatter of simulated operational intervals
    np.random.seed(42)
    k_samples = np.random.normal(38.2, 5.5, 45)
    k_samples = np.clip(k_samples, 15, 65)
    q_samples = []
    for ki in k_samples:
        base_qi = 3450 * (4 * (ki / 100) * (1 - 0.7 * (ki / 100))) / (4 * 0.48 * (1 - 0.7 * 0.48))
        q_samples.append(base_qi + np.random.normal(0, 95))

    ax.scatter(k_samples, q_samples, color="#58a6ff", alpha=0.6, s=35, edgecolors="#79c0ff", label="Amostras de Telemetria HFT")

    # Main MFD Curve line
    ax.plot(k, q, color="#00e5ff", linewidth=3, label="Curva Macroscópica Estimada (MFD)")

    # Critical point annotation
    ax.axvline(x=48.0, color="#ffd600", linestyle="--", linewidth=1.8, label="Ponto Crítico k_crit = 48.0 veic/km")
    ax.plot(48.0, 3450, marker="o", markersize=9, color="#ffd600")
    ax.annotate(
        "Capacidade Máxima Q_max\n3.450 veic/h",
        xy=(48.0, 3450),
        xytext=(55, 3200),
        arrowprops=dict(facecolor="#ffd600", shrink=0.08, width=1.5, headwidth=6),
        color="#ffd600",
        fontsize=10,
        fontweight="bold"
    )

    # Current operation marker
    curr_k = 38.2
    curr_q = 3280
    ax.plot(curr_k, curr_q, marker="*", markersize=14, color="#00ffcc", label="Ponto Operacional Atual CARINA")
    ax.annotate(
        f"Operação Atual\nk = {curr_k} veic/km\nQ = {curr_q} veic/h",
        xy=(curr_k, curr_q),
        xytext=(15, 2700),
        arrowprops=dict(facecolor="#00ffcc", shrink=0.08, width=1.5, headwidth=6),
        color="#00ffcc",
        fontsize=10,
        fontweight="bold"
    )

    # Formatting axes and styling
    ax.set_title("Diagrama Fundamental Macroscópico (MFD) - Malha Central Urbana", color="#f0f6fc", fontsize=14, pad=15, fontweight="bold")
    ax.set_xlabel("Densidade Média da Rede k (veículos / km)", color="#8b949e", fontsize=11, labelpad=10)
    ax.set_ylabel("Produção de Fluxo Q (veículos / hora)", color="#8b949e", fontsize=11, labelpad=10)
    ax.tick_params(colors="#8b949e", which="both", labelsize=10)

    for spine in ax.spines.values():
        spine.set_color("#30363d")

    ax.grid(True, linestyle=":", color="#30363d", alpha=0.7)
    ax.legend(loc="upper right", facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=9)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=150)
    plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_mfd_text_report() -> str:
    """Generates structured SLM Markdown text report for MFD optimization."""
    return """# NOXFORT CARINA - LAUDO DE OTIMIZAÇÃO MACROSCÓPICA (MFD)
**Unidade Operacional:** Centro de Controle Integrado de Tráfego  
**Módulo de Inteligência:** SLM Macroscopic Network Optimizer v2.4  
**Status do Laudo:** CONCLUÍDO | VÁLIDO PARA DESPACHO OPERACIONAL  

---

### 1. Resumo Executivo da Rede Viária
O motor analítico Macroscopic Fundamental Diagram (MFD) avaliou a acumulação veicular acumulada em todas as 4 interseções monitoradas. A rede opera com elevado grau de estabilidade, registrando um índice de homogeneidade de **92.4%**.

- **Capacidade Máxima Teórica ($Q_{max}$):** 3.450 veic/h
- **Densidade Crítica do Sistema ($k_{crit}$):** 48.0 veic/km
- **Densidade Atual Operacional:** 38.2 veic/km (Estado: **Regime Subcrítico de Alta Eficiência**)
- **Ganho de Fluidez Estimado:** +21.8% em relação ao plano de tempos fixos

---

### 2. Estratégias de Regulação Propostas pela IA

1. **Controle de Perímetro (Perimeter Metering):**
   - Modulação dinâmica de vazão nas vias de acesso radial (Av. Dom Pedro II e Estrada Ouro Fino).
   - Manutenção controlada da acumulação abaixo do limiar de saturação $k_{crit}$.

2. **Coordenação Semafórica em Onda Verde Dinâmica:**
   - Sincronização em cascata entre os nós `1116667894` e `1193472473`.
   - Offset temporal automatizado de 14.2 segundos ajustado à velocidade média de 36.5 km/h.

3. **Supressão de Retenções a Jusante:**
   - Prevenção ativa do fenômeno de spillback (retenção cruzada) no cruzamento `1193472566`.
   - Redução projetada de emissões de $\text{CO}_2$ da ordem de 14.3%.
"""


def generate_xai_plot_base64(agent_id: str = "1116667894") -> str:
    """Generates dark-themed feature attribution bar chart (Captum / Integrated Gradients)."""
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor="#0d1117", dpi=150)
    ax.set_facecolor("#161b22")

    features = [
        "Fila Norte-Sul (Q_NS)",
        "Tempo Máx. Espera (Wait_Max)",
        "Ocupação Laço 1 (Occ_Loop)",
        "Inflow a Montante (Inflow)",
        "Gradiente de Densidade",
        "Histórico Recente de Split"
    ]
    importance = [34.5, 26.2, 18.4, 11.8, 6.1, 3.0]

    y_pos = np.arange(len(features))
    colors = ["#00e5ff", "#00b0ff", "#2979ff", "#651fff", "#7c4dff", "#b388ff"]

    bars = ax.barh(y_pos, importance, color=colors, height=0.62, edgecolor="#ffffff", linewidth=0.3)

    for bar, val in zip(bars, importance):
        ax.text(
            bar.get_width() + 0.8,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center",
            ha="left",
            color="#f0f6fc",
            fontsize=10,
            fontweight="bold"
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(features, color="#f0f6fc", fontsize=10, fontweight="medium")
    ax.invert_yaxis()

    ax.set_xlim(0, 42)
    ax.set_title(f"Importância de Sensores (Integrated Gradients) - Agente {agent_id}", color="#f0f6fc", fontsize=14, pad=15, fontweight="bold")
    ax.set_xlabel("Atribuição Percentual na Decisão Semafórica (%)", color="#8b949e", fontsize=11, labelpad=10)
    ax.tick_params(colors="#8b949e", which="both", labelsize=10)

    for spine in ax.spines.values():
        spine.set_color("#30363d")

    ax.grid(True, axis="x", linestyle=":", color="#30363d", alpha=0.7)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=150)
    plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_xai_text_report(agent_id: str = "1116667894") -> str:
    """Generates structured XAI technical laudo."""
    return f"""# NOXFORT CARINA - LAUDO TÉCNICO DE EXPLICABILIDADE NEURAL (XAI)
**Agente Avaliado:** Interseção Semafórica #{agent_id}  
**Arquitetura Cognitiva:** Actor-Critic TCN com ST-GATv2 Spatio-Temporal Graph Attention  
**Método de Atribuição:** Integrated Gradients (Captum Engine - 50 passos de convergência)  
**Nível de Confiança:** 96.8% | **Supervisor Simbólico:** Guardian Agent Ativo  

---

### 1. Justificativa da Decisão Neural
O agente autônomo selecionou a extensão da **Fase 1 (Verde Corredor Principal)** por mais 12 segundos, postergando a transição de fase com base nas seguintes métricas sensoriais:

- **Fila na Aproximação Norte (34.5% de influência):** Detecção de pelotão compacto com 18 veículos em desaceleração. A abertura imediata permitiu a liberação de 92% da fila sem paradas adicionais.
- **Tempo de Espera Acumulado (26.2% de influência):** Veículos na transversal ainda não atingiram o limiar crítico de 45 segundos de espera, mantendo o atraso médio ponderado no valor ótimo.
- **Ocupação do Laço Indutivo (18.4% de influência):** Taxa de ocupação de 72% na faixa de tráfego direto.

---

### 2. Auditoria e Conformidade de Segurança (Guardian Agent)
- **Tempo Mínimo de Verde:** 15.0 segundos (RESPEITADO)
- **Tempo de Amarelo Regulamentar:** 3.5 segundos (ASSEGURADO)
- **Segurança de Pedestres:** Intervalo exclusivo de travessia preservado
- **Índice de Bloqueio em Cruzamento (Gridlock Score):** 0.02 (Seguro)
"""


def setup_demo_filesystem(base_output_dir: str):
    """Ensures mock files (status.json, checkpoints, captum dirs) exist in results/."""
    scenario_dir = os.path.join(base_output_dir, "results", "hft_live_session")
    os.makedirs(scenario_dir, exist_ok=True)

    # 1. status.json
    status_path = os.path.join(scenario_dir, "status.json")
    status_data = {
        "agent_ids": ["1116667894", "1193472473", "1193472566", "1193472678"],
        "status": "RUNNING",
        "step": 1420,
        "mode": "HFT_ADAPTIVE",
        "scenario": "hft_live_session"
    }
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=4)

    # 2. checkpoints
    checkpoints_dir = os.path.join(scenario_dir, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)
    for aid in status_data["agent_ids"]:
        chk = os.path.join(checkpoints_dir, f"agent_{aid}.pth")
        if not os.path.exists(chk):
            with open(chk, "wb") as f:
                f.write(b"MOCK_WEIGHTS_TCN")

    # 3. captum request/response dirs
    captum_dir = os.path.join(scenario_dir, "captum")
    req_dir = os.path.join(captum_dir, "requests")
    res_dir = os.path.join(captum_dir, "responses")
    os.makedirs(req_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    logging.info(f"[MockReportGenerator] Mock filesystem setup complete at: {scenario_dir}")
