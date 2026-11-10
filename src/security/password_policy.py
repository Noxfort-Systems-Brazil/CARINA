# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Password Policy Enforcement & Validation (SOLID: SRP & OCP).
Implements modern security standards aligned with OWASP & NIST guidelines,
while providing rich strength analysis for UI indicators.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.security.interfaces import IPasswordPolicy
from src.security.models import PasswordValidationResult


class ModernPasswordPolicy(IPasswordPolicy):
    """
    Validates password complexity against modern security standards:
    - Minimum 8 characters (up to 128)
    - At least one uppercase character (A-Z)
    - At least one lowercase character (a-z)
    - At least one numeric digit (0-9)
    - At least one special symbol (!@#$%^&*...)
    - Disallows surrounding whitespace
    """

    MIN_LENGTH = 8
    MAX_LENGTH = 128
    SPECIAL_CHARS_PATTERN = r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]"
    DEFAULT_SPECIAL_CHARS: Set[str] = set("!@#$%^&*()_+-=[]{}|;:,.<>?/~`\"'\\")

    def __init__(
        self,
        min_length: int = MIN_LENGTH,
        max_length: int = MAX_LENGTH,
        require_uppercase: bool = True,
        require_lowercase: bool = False,
        require_digit: bool = True,
        require_special: bool = True,
        disallow_surrounding_whitespace: bool = True,
        allowed_special_chars: Optional[Set[str]] = None,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.disallow_surrounding_whitespace = disallow_surrounding_whitespace
        self.allowed_special_chars = (
            allowed_special_chars if allowed_special_chars is not None else self.DEFAULT_SPECIAL_CHARS
        )

    def validate(self, password: str) -> PasswordValidationResult:
        """
        Validates password against all configured complexity requirements.
        Returns a PasswordValidationResult containing is_valid and list of error messages.
        """
        errors: List[str] = []

        if not isinstance(password, str) or not password:
            return PasswordValidationResult(
                is_valid=False,
                errors=["A senha não pode estar vazia."]
            )

        if self.disallow_surrounding_whitespace and (password.startswith(" ") or password.endswith(" ")):
            errors.append("A senha não deve começar nem terminar com espaços.")

        if len(password) < self.min_length:
            errors.append(f"A senha deve conter no mínimo {self.min_length} caracteres.")

        if len(password) > self.max_length:
            errors.append(f"A senha deve conter no máximo {self.max_length} caracteres.")

        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("A senha deve conter pelo menos uma letra maiúscula (A-Z).")

        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("A senha deve conter pelo menos uma letra minúscula (a-z).")

        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("A senha deve conter pelo menos um número (0-9).")

        if self.require_special:
            has_special = any(c in self.allowed_special_chars for c in password) or bool(
                re.search(self.SPECIAL_CHARS_PATTERN, password)
            )
            if not has_special:
                errors.append("A senha deve conter pelo menos um caractere especial (!@#$%^&*...).")

        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )

    @classmethod
    def check_criteria(cls, password: Optional[str]) -> Dict[str, bool]:
        """
        Evaluates each password criteria individually for UI indicators.
        Returns a dictionary of boolean flags.
        """
        if not password:
            return {
                "length": False,
                "numbers": False,
                "uppercase": False,
                "special": False,
                "lowercase": False,
            }

        return {
            "length": len(password) >= cls.MIN_LENGTH,
            "numbers": bool(re.search(r"\d", password)),
            "uppercase": bool(re.search(r"[A-Z]", password)),
            "special": bool(re.search(cls.SPECIAL_CHARS_PATTERN, password)),
            "lowercase": bool(re.search(r"[a-z]", password)),
        }

    @classmethod
    def validate_legacy(cls, password: Optional[str]) -> Tuple[bool, List[str]]:
        """
        Legacy validation returning (is_valid, missing_criteria_keys).
        Provided for compatibility with older UI components and tests.
        """
        if not password:
            return False, ["length", "numbers", "uppercase", "special"]

        criteria = cls.check_criteria(password)
        mandatory_keys = ["length", "numbers", "uppercase", "special"]
        missing = [k for k in mandatory_keys if not criteria.get(k, False)]
        return len(missing) == 0, missing

    @classmethod
    def calculate_strength(cls, password: Optional[str]) -> Dict[str, Any]:
        """
        Calculates strength score, progress bar percentage, classification level,
        and criteria breakdown for UI indicators.
        """
        if not password:
            return {
                "score": 0,
                "level": "none",
                "progress": 0.0,
                "is_valid": False,
                "criteria": cls.check_criteria(""),
                "missing": ["length", "numbers", "uppercase", "special"],
            }

        criteria = cls.check_criteria(password)
        is_valid, missing = cls.validate_legacy(password)

        raw_score = 0.0
        if criteria["length"]:
            raw_score += 1.0
        if criteria["numbers"]:
            raw_score += 1.0
        if criteria["uppercase"]:
            raw_score += 1.0
        if criteria["special"]:
            raw_score += 1.0

        if criteria["lowercase"]:
            raw_score += 0.5
        if len(password) >= 12:
            raw_score += 0.5
        if len(password) >= 16:
            raw_score += 0.5
        if len(re.findall(r"\d", password)) >= 2:
            raw_score += 0.25
        if len(re.findall(cls.SPECIAL_CHARS_PATTERN, password)) >= 2:
            raw_score += 0.25

        if raw_score <= 1.5:
            level = "very_weak"
            progress = 0.2
            score_category = 1
        elif raw_score <= 2.5:
            level = "weak"
            progress = 0.4
            score_category = 2
        elif raw_score < 4.0:
            level = "medium"
            progress = 0.6
            score_category = 3
        elif raw_score < 5.0:
            level = "strong"
            progress = 0.8
            score_category = 4
        else:
            level = "very_strong"
            progress = 1.0
            score_category = 5

        return {
            "score": score_category,
            "raw_score": raw_score,
            "level": level,
            "progress": progress,
            "is_valid": is_valid,
            "criteria": criteria,
            "missing": missing,
        }


class PasswordValidator(ModernPasswordPolicy):
    """
    Direct backward-compatible class with static methods for CARINA UI and tests.
    """

    @classmethod
    def validate(cls, password: Optional[str]) -> Tuple[bool, List[str]]:  # type: ignore[override]
        """Legacy validate returning (is_valid, missing_keys)."""
        return cls.validate_legacy(password)
