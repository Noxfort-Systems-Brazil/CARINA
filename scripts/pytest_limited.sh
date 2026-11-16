#!/usr/bin/env bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Runs pytest inside a hard kernel memory limit:
#   1. Prefers systemd user cgroup v2 scope (MemoryHigh / MemoryMax / MemorySwapMax),
#      capping physical RAM, page cache, and all spawned subprocesses together.
#   2. Falls back to ulimit -d + CARINA_PYTEST_MAX_RAM_MB process-tree RSS guard
#      when systemd user sessions are unavailable (e.g. minimal CI containers).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [ -x "${REPO_ROOT}/.venv/bin/pytest" ]; then
    PYTEST_BIN="${REPO_ROOT}/.venv/bin/pytest"
else
    PYTEST_BIN="$(command -v pytest)"
fi

PYTEST_MEM_HIGH="${PYTEST_MEM_HIGH:-1536M}"
PYTEST_MEM_MAX="${PYTEST_MEM_MAX:-2048M}"
PYTEST_SWAP_MAX="${PYTEST_SWAP_MAX:-512M}"

_to_mb() {
    local val="${1^^}"
    case "${val}" in
        *G) echo $(( ${val%G} * 1024 )) ;;
        *M) echo $(( ${val%M} )) ;;
        *K) echo $(( ${val%K} / 1024 )) ;;
        *)  echo "${val}" ;;
    esac
}

MAX_RAM_MB="${CARINA_PYTEST_MAX_RAM_MB:-$(_to_mb "${PYTEST_MEM_MAX}")}"
export CARINA_PYTEST_MAX_RAM_MB="${MAX_RAM_MB}"
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export MPLBACKEND="${MPLBACKEND:-Agg}"

if command -v systemd-run >/dev/null 2>&1 && systemd-run --user --scope --quiet -p MemoryMax=64M true >/dev/null 2>&1; then
    echo "[pytest_limited] cgroup v2 limits: MemoryHigh=${PYTEST_MEM_HIGH}, MemoryMax=${PYTEST_MEM_MAX}, MemorySwapMax=${PYTEST_SWAP_MAX}"
    exec systemd-run --user --scope --quiet \
        -p "MemoryHigh=${PYTEST_MEM_HIGH}" \
        -p "MemoryMax=${PYTEST_MEM_MAX}" \
        -p "MemorySwapMax=${PYTEST_SWAP_MAX}" \
        -p "MemoryAccounting=yes" \
        "${PYTEST_BIN}" "$@"
else
    DATA_LIMIT_KB=$(( MAX_RAM_MB * 1024 ))
    echo "[pytest_limited] systemd-run unavailable; applying ulimit -d ${DATA_LIMIT_KB}K and CARINA_PYTEST_MAX_RAM_MB=${MAX_RAM_MB}"
    ulimit -d "${DATA_LIMIT_KB}" 2>/dev/null || true
    exec "${PYTEST_BIN}" "$@"
fi
