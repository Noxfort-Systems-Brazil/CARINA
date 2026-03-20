# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY;
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: Dockerfile
# Author: Gabriel Moraes
# Date: 28 de Outubro de 2025
#
# Descrição:
# Este Dockerfile é otimizado para PyInstaller e PyTorch (com CUDA).
# Ele usa um build multi-stage para manter a imagem final leve.
# =====================================================================
# ESTÁGIO 1: BUILDER
# Baseado na imagem oficial do PyTorch com CUDA 11.8 
# =====================================================================
FROM pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime AS builder

# Define o diretório de trabalho
WORKDIR /app

# Define variáveis de ambiente para evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    patchelf \
    upx \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Atualiza o pip
RUN pip install --upgrade pip

# Copia o arquivo de requisitos de build
COPY build-requirements.txt .
# Instala os requisitos de Python
RUN pip install --no-cache-dir -r build-requirements.txt

# Copia todo o código-fonte do CARINA para o container
COPY . .

# Executa o PyInstaller
RUN pyinstaller --noconfirm carina.spec

# =====================================================================
# ESTÁGIO 2: FINAL
# Apenas extrai o pacote
# =====================================================================
FROM ubuntu:24.04

WORKDIR /app

# Define variáveis de ambiente para evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Copia o executável construído do estágio anterior
COPY --from=builder /app/dist/carina /app/dist/carina