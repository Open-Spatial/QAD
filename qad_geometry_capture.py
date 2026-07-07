# -*- coding: utf-8 -*-
"""Result objects for QAD geometry capture integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QadGeometryCaptureResult:
   command_name: str
   status: str
   geometries: list[Any] = field(default_factory=list)
   message: str = ""
   selections: list[dict[str, Any]] = field(default_factory=list)
