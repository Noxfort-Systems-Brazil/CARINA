#!/usr/bin/env bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DEMO_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "🎬 NOXFORT CARINA - GERADOR DE VÍDEO DO VIDEOWALL CCO"
echo "=========================================================="

# 1. Clear any lingering process on ports 2201 and 8085
for PORT in 2201 8085; do
  if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "🧹 Liberando porta $PORT..."
    kill -9 $(lsof -ti:$PORT) 2>/dev/null || true
  fi
done
sleep 1

# 2. Start Go Gateway in background with stdin kept open
echo "🚀 Iniciando Go Hardware & Web Gateway (Porta 2201)..."
tail -f /dev/null | bin/carina-go -web-enabled > /tmp/carina_go_gateway.log 2>&1 &
GATEWAY_PID=$!

# 3. Start EVP Fleet Telemetry Simulator in background
echo "🚑 Iniciando Simulador de Frota de Emergência (EVP Multi-Corporação)..."
.venv/bin/python demo/evp_vehicle_simulator.py --port 2201 --mode patrol --duration 120 > /tmp/carina_evp_sim.log 2>&1 &
SIM_PID=$!

cleanup() {
  echo ""
  echo "🛑 Encerrando simulador e gateway CCO..."
  kill $SIM_PID 2>/dev/null || true
  kill $GATEWAY_PID 2>/dev/null || true
  for PORT in 2201 8085; do
    if lsof -ti:$PORT >/dev/null 2>&1; then
      kill -9 $(lsof -ti:$PORT) 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

# 4. Wait for CCO web server readiness on port 2201
echo "⏳ Aguardando Videowall CCO inicializar em http://127.0.0.1:2201/cco/..."
MAX_RETRIES=20
COUNT=0
until curl -s -I http://127.0.0.1:2201/cco/ >/dev/null 2>&1; do
  sleep 0.8
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "❌ Erro: Tempo limite excedido aguardando Videowall CCO."
    cat /tmp/carina_go_gateway.log
    exit 1
  fi
done

echo "✅ Servidor CCO pronto! Iniciando gravação automatizada via Playwright..."

# 5. Execute orchestrated CCO recording
node "$DEMO_DIR/record_cco.cjs"

# 6. Final validation
FINAL_VIDEO="$DEMO_DIR/recordings/carina_cco_apresentacao.mp4"
if [ -f "$FINAL_VIDEO" ]; then
  echo "=========================================================="
  echo "🎉 GRAVAÇÃO DO VIDEOWALL CCO CONCLUÍDA COM SUCESSO!"
  echo "=========================================================="
  ls -lh "$FINAL_VIDEO"
  echo ""
  echo "Verificação FFprobe:"
  ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 "$FINAL_VIDEO"
  echo "=========================================================="
else
  echo "❌ Erro: O arquivo de vídeo final CCO não foi gerado."
  exit 1
fi
