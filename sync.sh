#!/usr/bin/env bash
# ==============================================================================
# CARINA - Script de Sincronização e Push Automatizado
# Uso:
#   ./sync.sh "mensagem do commit"
#   ./sync.sh                     (usa mensagem automática com data/hora)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
COMMIT_MSG="$1"

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="chore: update CARINA modules ($(date '+%Y-%m-%d %H:%M:%S'))"
fi

echo -e "${BLUE}=== [CARINA] Sincronizando com GitHub ===${NC}"
echo -e "${BLUE}Branch atual:${NC} ${BRANCH}"

echo -e "${BLUE}1/3 Adicionando arquivos...${NC}"
git add -A

if git diff --cached --quiet; then
    echo -e "${YELLOW}Nenhuma alteração nova para comitar.${NC}"
else
    echo -e "${BLUE}2/3 Comitando: \"${COMMIT_MSG}\"...${NC}"
    git commit -m "$COMMIT_MSG"
fi

echo -e "${BLUE}3/3 Enviando para o GitHub (origin ${BRANCH})...${NC}"
git push origin "$BRANCH"

echo -e "${GREEN}✔ CARINA atualizada com sucesso no GitHub!${NC}"
