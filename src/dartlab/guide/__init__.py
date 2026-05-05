"""guide — 사용자 안내 데스크 (모든 레이어에서 import 가능).

축 카탈로그 빌더(buildAxisGuideDataFrame)와 에러 복구 안내 템플릿
(missingDataHint, apiKeyMissingHint)을 SSOT 로 제공한다. 각 엔진은
이 모듈을 참조만 하고 중복 구현하지 않는다.

엔진 `_guide()` 메서드는 엔진별 _AXIS_REGISTRY 차이(group 로직,
extra 컬럼)를 콜러블 주입으로 흡수해 한 블록으로 축소된다.
"""

from dartlab.guide.axisGuide import buildAxisGuideDataFrame
from dartlab.guide.errors import apiKeyMissingHint, missingDataHint

__all__ = ["buildAxisGuideDataFrame", "missingDataHint", "apiKeyMissingHint"]
