#!/usr/bin/env bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

MAX_FILES=50
MAX_LINES=3000
FORCE=0

ARGS=()
for arg in "$@"; do
    if [ "$arg" == "--force" ]; then
        FORCE=1
    else
        ARGS+=("$arg")
    fi
done

COMMIT_MSG="${ARGS[0]:-}"
PATHS=("${ARGS[@]:1}")

if [ -z "$COMMIT_MSG" ]; then
    echo -e "${RED}Erro: Mensagem de commit obrigatória.${NC}"
    echo -e "Uso: $0 \"<tipo>(<escopo>): <descrição>\" [caminhos...] [--force]"
    exit 1
fi

if ! echo "$COMMIT_MSG" | grep -Eq '^(feat|fix|refactor|test|chore|docs|perf|ci|build|style)(\([a-zA-Z0-9_/-]+\))?!?: .+'; then
    echo -e "${RED}Erro: A mensagem deve seguir o padrão Conventional Commits (ex: 'feat(engine): add spillback penalty').${NC}"
    exit 1
fi

BRANCH=$(git branch --show-current 2>/dev/null || echo "main")

echo -e "${BLUE}=== [CARINA] Sincronizando com GitHub ===${NC}"
echo -e "${BLUE}Branch atual:${NC} ${BRANCH}"

if [ "${#PATHS[@]}" -gt 0 ]; then
    echo -e "${BLUE}1/3 Adicionando caminhos especificados (${PATHS[*]})...${NC}"
    git add -- "${PATHS[@]}"
elif git diff --cached --quiet; then
    echo -e "${YELLOW}Aviso: Nenhum caminho informado e stage vazio. Use 'git add <arquivos>' ou passe os caminhos para o script.${NC}"
    exit 1
else
    echo -e "${BLUE}1/3 Usando arquivos já preparados no stage (git index)...${NC}"
fi

if git diff --cached --quiet; then
    echo -e "${YELLOW}Nenhuma alteração nova no stage para comitar.${NC}"
    exit 0
fi

STAGED_FILES=$(git diff --cached --name-only | wc -l)
STAGED_LINES=$(git diff --cached --numstat | awk '{added+=$1; deleted+=$2} END {print added+deleted+0}')

if [ "$FORCE" -eq 0 ] && { [ "$STAGED_FILES" -gt "$MAX_FILES" ] || [ "$STAGED_LINES" -gt "$MAX_LINES" ]; }; then
    echo -e "${RED}Bloqueado: Commit excede os limites de higiene (${STAGED_FILES}/${MAX_FILES} arquivos, ${STAGED_LINES}/${MAX_LINES} linhas).${NC}"
    echo -e "${YELLOW}Divida as alterações em commits atômicos por módulo ou passe --force se for intencional.${NC}"
    exit 1
fi

echo -e "${BLUE}2/3 Comitando (${STAGED_FILES} arquivos, ${STAGED_LINES} linhas): \"${COMMIT_MSG}\"...${NC}"
git commit -m "$COMMIT_MSG"

echo -e "${BLUE}3/3 Enviando para o GitHub (origin ${BRANCH})...${NC}"
git push origin "$BRANCH"

echo -e "${GREEN}✔ CARINA atualizada com sucesso no GitHub!${NC}"
