"""sections BUILD — zip → 14-col period-sharded parquet (손실0/dup0).

BUILD-time 전용 (lxml / zipfile). RUNTIME reader 와 물리 분리 — 본 패키지를
import 할 때만 lxml 이 로드된다 (reader 경로는 lxml import 0).

공개: ``buildSections`` / ``buildSectionsBaseline`` / ``buildSectionsAll``.
CLI: ``python -m dartlab.providersV2.dart.sections.build.builder --codes 005930,...``
"""

from __future__ import annotations

from .builder import buildSections, buildSectionsAll, buildSectionsBaseline

__all__ = ["buildSections", "buildSectionsAll", "buildSectionsBaseline"]
