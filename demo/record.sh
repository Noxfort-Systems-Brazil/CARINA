#!/usr/bin/env bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DEMO_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "🎬 NOXFORT CARINA - GERADOR DE VÍDEO DE APRESENTAÇÃO"
echo "=========================================================="

# 1. Clear any lingering process on port 8550
if lsof -ti:8550 >/dev/null 2>&1; then
  echo "🧹 Liberando porta 8550..."
  kill -9 $(lsof -ti:8550) 2>/dev/null || true
  sleep 1
fi

# 2. Initialize Demo Backend in background
echo "🚀 Iniciando servidor Flet CARINA em modo de apresentação..."
.venv/bin/python demo/demo_launcher.py > /tmp/carina_demo_server.log 2>&1 &
SERVER_PID=$!

cleanup() {
  echo ""
  echo "🛑 Encerrando servidor de demonstração (PID: $SERVER_PID)..."
  kill $SERVER_PID 2>/dev/null || true
  if lsof -ti:8550 >/dev/null 2>&1; then
    kill -9 $(lsof -ti:8550) 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# 3. Wait for server response on port 8550
echo "⏳ Aguardando CARINA inicializar em http://127.0.0.1:8550..."
MAX_RETRIES=20
COUNT=0
until curl -s -I http://127.0.0.1:8550 >/dev/null 2>&1; do
  sleep 0.8
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "❌ Erro: Tempo limite excedido aguardando servidor CARINA."
    cat /tmp/carina_demo_server.log
    exit 1
  fi
done

echo "✅ Servidor pronto! Iniciando gravação automatizada via Playwright..."

# 4. Execute orchestrated recording
node "$DEMO_DIR/record_presentation.cjs"

# 5. Final validation of generated file
FINAL_VIDEO="$DEMO_DIR/recordings/carina_apresentacao.mp4"
if [ -f "$FINAL_VIDEO" ]; then
  echo "=========================================================="
  echo "🎉 GRAVAÇÃO CONCLUÍDA COM SUCESSO!"
  echo "=========================================================="
  ls -lh "$FINAL_VIDEO"
  echo ""
  echo "Verificação FFprobe:"
  ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 "$FINAL_VIDEO"
  echo "=========================================================="
else
  echo "❌ Erro: O arquivo de vídeo final não foi gerado."
  exit 1
fi
