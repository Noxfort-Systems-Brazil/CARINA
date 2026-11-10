#!/bin/bash
# CARINA Debian Package Builder Runner
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd )"
DIST_DIR="$PROJECT_ROOT/dist"

echo "=========================================================================="
echo " 🚀 Iniciando Build Hermético do Instalador .deb da CARINA via Docker"
echo "=========================================================================="
echo "Diretório do Projeto: $PROJECT_ROOT"
echo "Diretório de Saída:   $DIST_DIR"
echo ""

mkdir -p "$DIST_DIR"

# Verify Docker availability
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Erro: Docker não está instalado ou não foi encontrado no PATH." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "❌ Erro: O daemon do Docker não está acessível (verifique permissões do usuário)." >&2
    exit 1
fi

cd "$PROJECT_ROOT"

echo "📦 Compilando estágios: CCO (React), Go Gateway, Python venv e .deb..."

if docker buildx version >/dev/null 2>&1; then
    echo "⚙️  Utilizando Docker Buildx com exportador local direto..."
    docker buildx build \
        --file packaging/Dockerfile.build \
        --target export \
        --output type=local,dest="$DIST_DIR" \
        .
    echo "✅ Buildx concluiu com sucesso e exportou o pacote para $DIST_DIR!"
else
    echo "⚙️  Docker Buildx não detectado. Utilizando compilação multi-stage com extração atômica..."
    IMAGE_TAG="carina-deb-builder:latest"
    DOCKER_BUILDKIT=0 docker build -f packaging/Dockerfile.build --target packager -t "$IMAGE_TAG" .
    CONTAINER_ID=$(docker create "$IMAGE_TAG")
    docker cp "$CONTAINER_ID:/dist/carina_1.0.0_amd64.deb" "$DIST_DIR/"
    docker rm "$CONTAINER_ID" >/dev/null
    echo "✅ Compilação concluiu com sucesso e exportou o pacote para $DIST_DIR!"
fi

echo ""
echo "=========================================================================="
echo " 🎉 Pacote .deb gerado com sucesso!"
echo "=========================================================================="
ls -lh "$DIST_DIR/carina_1.0.0_amd64.deb"
echo ""

if command -v dpkg-deb >/dev/null 2>&1; then
    echo "📋 Informações do Pacote:"
    dpkg-deb -I "$DIST_DIR/carina_1.0.0_amd64.deb"
fi

echo ""
echo "Para instalar em qualquer máquina Ubuntu/Debian:"
echo "  sudo apt install ./dist/carina_1.0.0_amd64.deb"
echo "=========================================================================="
