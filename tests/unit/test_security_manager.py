# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: tests/unit/test_security_manager.py
# Author: Gabriel Moraes
# Date: September 2026

import hashlib
import os
import shutil
import tempfile

import pytest

from src.utils.security_manager import SecurityManager


@pytest.fixture
def temp_security_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_production_mode_strictly_blocks_admin_admin(temp_security_dir, monkeypatch):
    """Garante que em ambiente de produção admin:admin é terminantemente bloqueado."""
    monkeypatch.setenv("CARINA_ENV", "production")
    monkeypatch.setenv("CARINA_SUPERUSER_USER", "prod_superuser")
    monkeypatch.setenv("CARINA_SUPERUSER_PASSWORD", "SuperSecurePassword123!")

    sm = SecurityManager()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    assert sm.is_production is True
    assert sm.master_user == "prod_superuser"

    # Tentativa com admin:admin DEVE FALHAR
    success, msg = sm.authenticate("admin", "admin")
    assert success is False
    assert "Invalid credentials" in msg or "invalid" in msg.lower()

    # Tentativa com superusuário real DEVE SUCEDER
    success_prod, role = sm.authenticate("prod_superuser", "SuperSecurePassword123!")
    assert success_prod is True
    assert role == "MASTER"


def test_development_mode_allows_admin_admin_for_github(temp_security_dir, monkeypatch):
    """Garante que no ambiente de desenvolvimento (clone do GitHub) admin:admin funciona normalmente."""
    monkeypatch.setenv("CARINA_ENV", "development")
    monkeypatch.delenv("CARINA_SUPERUSER_USER", raising=False)
    monkeypatch.delenv("CARINA_SUPERUSER_PASSWORD", raising=False)
    monkeypatch.delenv("CARINA_SUPERUSER_HASH", raising=False)

    sm = SecurityManager()
    sm.is_production = False
    sm.master_user = "admin"
    sm.master_hash = hashlib.sha256("admin".encode("utf-8")).hexdigest()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    assert sm.is_production is False
    assert sm.master_user == "admin"

    # admin:admin DEVE SUCEDER no modo de teste
    success, role = sm.authenticate("admin", "admin")
    assert success is True
    assert role in ["SUPERUSER", "MASTER"]


def test_add_user_allows_update_and_blocks_insecure_pwd_in_prod(temp_security_dir, monkeypatch):
    """Garante atualização de senhas e bloqueio de senha 'admin' em produção."""
    monkeypatch.setenv("CARINA_ENV", "production")
    monkeypatch.setenv("CARINA_SUPERUSER_USER", "prod_master")
    monkeypatch.setenv("CARINA_SUPERUSER_PASSWORD", "Secret123!")

    sm = SecurityManager()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    # Em produção, adicionar ou alterar senha para 'admin' deve ser rejeitado
    assert sm.add_user("testuser", "admin", "SUPERUSER") is False

    # Adicionar com senha forte deve funcionar
    assert sm.add_user("testuser", "StrongPass456!", "SUPERUSER") is True

    # Atualizar senha existente deve funcionar
    assert sm.add_user("testuser", "NewStrongPass789!", "SUPERUSER") is True
    success, role = sm.authenticate("testuser", "NewStrongPass789!")
    assert success is True
    assert role == "SUPERUSER"
