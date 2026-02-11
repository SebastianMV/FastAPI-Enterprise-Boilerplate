# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Domain value objects package."""

from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password

__all__ = [
    "Email",
    "Password",
]
