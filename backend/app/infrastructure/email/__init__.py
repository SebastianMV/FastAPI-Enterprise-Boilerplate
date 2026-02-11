# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Email infrastructure module.

Provides email templates with i18n support and email sending capabilities.
"""

from app.infrastructure.email.service import EmailService, get_email_service
from app.infrastructure.email.templates import EmailTemplate, EmailTemplateEngine

__all__ = [
    "EmailService",
    "get_email_service",
    "EmailTemplateEngine",
    "EmailTemplate",
]
