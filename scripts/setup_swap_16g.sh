#!/usr/bin/env bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

if [ "$EUID" -ne 0 ]; then
    echo "[-] Erro: Este script precisa ser executado como root (use: sudo bash scripts/setup_swap_16g.sh)" >&2
    exit 1
fi

SWAP_FILE="/swap.img"
SWAP_SIZE="16G"

echo "[*] Iniciando configuração do Swap para ${SWAP_SIZE}..."

# 1. Deactivate current swap if in use
if grep -q "${SWAP_FILE}" /proc/swaps; then
    echo "[*] Desativando swap atual (${SWAP_FILE})..."
    swapoff "${SWAP_FILE}"
fi

# 2. Allocate 16 GB in file
echo "[*] Alocando ${SWAP_SIZE} em ${SWAP_FILE}..."
if ! fallocate -l "${SWAP_SIZE}" "${SWAP_FILE}" 2>/dev/null; then
    echo "[!] fallocate falhou ou sistema de arquivos não suporta, utilizando dd..."
    dd if=/dev/zero of="${SWAP_FILE}" bs=1M count=16384 status=progress
fi

# 3. Strict permissions (only root can read/write)
echo "[*] Definindo permissões 600..."
chmod 600 "${SWAP_FILE}"

# 4. Format as swap
echo "[*] Formatando ${SWAP_FILE} como swap..."
mkswap "${SWAP_FILE}"

# 5. Activate swap
echo "[*] Ativando novo swap..."
swapon "${SWAP_FILE}"

# 6. Ensure persistence in fstab
if ! grep -q "${SWAP_FILE}" /etc/fstab; then
    echo "[*] Adicionando ${SWAP_FILE} ao /etc/fstab para inicialização persistente..."
    echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
fi

echo ""
echo "[✓] Swap configurado com sucesso!"
echo "--- Resumo Atual do Swap ---"
swapon --show
echo ""
echo "--- Memória Geral do Sistema ---"
free -h
