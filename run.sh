#!/bin/bash
# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: run.sh
# Author: Gabriel Moraes
# Date: September 2026

# Navega para o diretório raiz do projeto (onde o script está localizado)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

# Ativa o ambiente virtual
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Erro: Ambiente virtual (.venv) não encontrado no diretório $SCRIPT_DIR"
    exit 1
fi

# Executa o script python repassando eventuais argumentos
python carina.py "$@"
