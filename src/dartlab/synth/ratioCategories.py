"""재무비율 카테고리 호환 re-export.

새 SSOT는 ``dartlab.core.ratioCategories``다. 기존
``dartlab.synth.ratioCategories`` import 경로를 보존하기 위해 이 모듈은
상수만 다시 내보낸다.
"""

from __future__ import annotations

from dartlab.core.ratioCategories import RATIO_CATEGORIES as RATIO_CATEGORIES
