# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class MaturityRepositoryPort(Protocol):
    """
    Persistence Port (Interface) for saving and loading agent maturity states.
    Decouples domain/core logic from infrastructure storage implementations.
    """

    def save(self, filepath: str, state: Dict[str, Any], locale_manager: Any = None) -> bool:
        """Saves maturity state dictionary to storage."""
        ...

    def load(self, filepath: str, locale_manager: Any = None) -> Optional[Dict[str, Any]]:
        """Loads maturity state dictionary from storage."""
        ...
