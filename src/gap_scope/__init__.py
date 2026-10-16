"""Classify PR / commit changes into gap-analysis scope parameters."""

from __future__ import annotations

from gap_scope.classifier import GapScope, classify_changed_paths

__all__ = ["GapScope", "classify_changed_paths"]
