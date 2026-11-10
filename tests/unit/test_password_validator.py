# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import pytest

from src.security.config import SecurityConfig
from src.security.crypto import PBKDF2PasswordHasher
from src.security.password_policy import PasswordValidator
from src.security.account_manager import UserAccountManager as UserManagementService
from ui.cards.account_settings_card import AccountSettingsCard


class InMemoryUserRepository:
    def __init__(self, users=None):
        self.users = users or {}

    def get_user(self, username):
        return self.users.get(username)

    def set_user(self, username, password_hash, role):
        is_update = username in self.users
        self.users[username] = {"hash": password_hash, "role": role}
        return is_update

    def delete_user(self, username):
        if username in self.users:
            del self.users[username]
            return True
        return False

    def list_users(self):
        return [{"username": u, "role": d["role"]} for u, d in self.users.items()]

    def ensure_default_user(self, is_production, master_user, default_hash):
        pass


def test_password_validator_check_criteria():
    assert PasswordValidator.check_criteria(None) == {
        "length": False,
        "numbers": False,
        "uppercase": False,
        "special": False,
        "lowercase": False,
    }

    assert PasswordValidator.check_criteria("") == {
        "length": False,
        "numbers": False,
        "uppercase": False,
        "special": False,
        "lowercase": False,
    }

    # Length < 8
    crit = PasswordValidator.check_criteria("Ab1!")
    assert crit["length"] is False
    assert crit["uppercase"] is True
    assert crit["lowercase"] is True
    assert crit["numbers"] is True
    assert crit["special"] is True

    # 8 digits
    crit_digits = PasswordValidator.check_criteria("12345678")
    assert crit_digits["length"] is True
    assert crit_digits["numbers"] is True
    assert crit_digits["uppercase"] is False
    assert crit_digits["special"] is False

    # Fully compliant
    crit_full = PasswordValidator.check_criteria("Abcdef123!")
    assert all(crit_full.values()) is True


def test_password_validator_validate():
    # Empty / None
    is_valid, missing = PasswordValidator.validate(None)
    assert is_valid is False
    assert set(missing) == {"length", "numbers", "uppercase", "special"}

    is_valid, missing = PasswordValidator.validate("")
    assert is_valid is False

    # Insecure passwords
    assert PasswordValidator.validate("admin")[0] is False
    assert PasswordValidator.validate("12345678")[0] is False
    assert PasswordValidator.validate("password")[0] is False
    assert PasswordValidator.validate("Password123")[0] is False  # Missing special
    assert PasswordValidator.validate("Password!")[0] is False  # Missing numbers
    assert PasswordValidator.validate("password123!")[0] is False  # Missing uppercase

    # Valid passwords
    assert PasswordValidator.validate("Password123!")[0] is True
    assert PasswordValidator.validate("12345678A!")[0] is True  # 8 numbers + upper + special
    assert PasswordValidator.validate("StrongPass456!")[0] is True
    assert PasswordValidator.validate("NewStrongPass789!")[0] is True
    assert PasswordValidator.validate("OpPass123!")[0] is True


def test_password_validator_calculate_strength():
    # Empty
    res_empty = PasswordValidator.calculate_strength("")
    assert res_empty["level"] == "none"
    assert res_empty["progress"] == 0.0
    assert res_empty["is_valid"] is False

    # Very weak
    res_vw = PasswordValidator.calculate_strength("abc")
    assert res_vw["level"] == "very_weak"
    assert res_vw["progress"] <= 0.4
    assert res_vw["is_valid"] is False

    # Weak (e.g. 8 digits or 8 lowercase letters)
    res_w = PasswordValidator.calculate_strength("12345678")
    assert res_w["level"] in ["weak", "medium"]
    assert res_w["is_valid"] is False

    # Medium (missing special char or numbers)
    res_med = PasswordValidator.calculate_strength("Password12")
    assert res_med["level"] in ["medium", "weak"]
    assert res_med["is_valid"] is False

    # Strong
    res_strong = PasswordValidator.calculate_strength("Pass123!")
    assert res_strong["level"] == "strong"
    assert res_strong["is_valid"] is True
    assert res_strong["progress"] == 0.8

    # Very strong
    res_vstrong = PasswordValidator.calculate_strength("Super#Strong&Password2026!")
    assert res_vstrong["level"] == "very_strong"
    assert res_vstrong["progress"] == 1.0
    assert res_vstrong["is_valid"] is True


def test_user_management_service_rejects_insecure_passwords():
    hasher = PBKDF2PasswordHasher(iterations=1000)
    user_repo = InMemoryUserRepository()
    config = SecurityConfig(
        security_file="sec.json",
        lockdown_file="lock.flag",
        is_production=False,
        master_user="admin",
        master_hash="hash",
        max_failed_attempts=3,
    )

    user_svc = UserManagementService(config, user_repo, hasher)

    # Insecure passwords must be rejected even in development mode
    assert user_svc.add_user("user1", "admin", "OPERATOR") is False
    assert user_svc.add_user("user2", "12345678", "OPERATOR") is False
    assert user_svc.add_user("user3", "Password123", "OPERATOR") is False
    assert user_svc.add_user("user4", "Password!", "OPERATOR") is False

    # Strong password must succeed
    assert user_svc.add_user("user5", "StrongPass123!", "OPERATOR") is True
    assert user_svc.add_user("user6", "12345678A!", "SUPERUSER") is True
    assert len(user_svc.list_users()) == 2


def test_account_settings_card_ui_behavior():
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda key, default="": default

    on_add = MagicMock()
    on_remove = MagicMock()
    on_list = MagicMock()

    card = AccountSettingsCard(
        locale_manager=mock_locale,
        on_add_user=on_add,
        on_remove_user=on_remove,
        on_request_list=on_list,
    )

    # Initial state
    assert card.strength_bar.value == 0.0
    assert card.strength_status.value == "Não informada"

    # Typing insecure password
    card.password_field.value = "12345678"
    card._on_password_change(None)
    assert card.crit_length_icon.name == "check_circle_rounded"
    assert card.crit_num_icon.name == "check_circle_rounded"
    assert card.crit_upper_icon.name == "radio_button_unchecked"
    assert card.crit_spec_icon.name == "radio_button_unchecked"

    # Attempting to add with insecure password
    card.username_field.value = "novo_usuario"
    card._add_user(None)
    assert on_add.called is False
    assert card.password_field.error_text is not None

    # Typing secure password
    card.password_field.value = "SenhaForte123!"
    card._on_password_change(None)
    assert card.crit_length_icon.name == "check_circle_rounded"
    assert card.crit_upper_icon.name == "check_circle_rounded"
    assert card.crit_num_icon.name == "check_circle_rounded"
    assert card.crit_spec_icon.name == "check_circle_rounded"
    assert card.strength_bar.value >= 0.75

    # Adding user with secure password
    card._add_user(None)
    assert on_add.called is True
    on_add.assert_called_once_with("novo_usuario", "SenhaForte123!", "OPERATOR")
    assert card.username_field.value == ""
    assert card.password_field.value == ""
    assert card.strength_bar.value == 0.0

    # Test empty username error
    card.password_field.value = "SenhaForte123!"
    card._add_user(None)
    assert card.username_field.error_text is not None

    # Test update_translations
    mock_locale.get_string.side_effect = lambda key, default="": f"tr_{key}"
    card.update_translations(mock_locale)
    assert card.title_text.value == "tr_accounts.title"
    assert card.strength_title.value == "tr_accounts.password_strength"

