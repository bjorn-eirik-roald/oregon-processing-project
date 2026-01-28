# -*- coding: utf-8 -*-
"""
Display Constants - Centralized formatting and display parameters.

Defines constants used across multiple modules for consistent output formatting.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayConstants:
    """Centralized constants for output formatting and display."""

    # Line lengths for section separators
    SECTION_LINE_LENGTH: int = 70
    SUBSECTION_LINE_LENGTH: int = 40

    # Section separator characters
    SECTION_SEPARATOR: str = "="
    SUBSECTION_SEPARATOR: str = "-"


# Singleton instance for import
display = DisplayConstants()
