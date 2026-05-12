"""synth — L1.5 분석 후처리/매칭/시나리오.

분석 결과 + scan 결과 + 룰 (reference) 을 결합해 매칭·분류·시나리오 후처리.
현 dartlab.synth + indicators·axisGuide·ratioCategories·overrides 가
본 위치로 이동 예정 (P-CORE B). 본 단계는 골격만.

룰 (operation.architecture SSOT):
- import OK: dartlab.core, dartlab.gather, dartlab.providers
- import 금지: dartlab.{scan, frame, reference} (L1.5 4 형제 cross 금지)
- 진입 조건: ≥ 2 분석엔진이 같은 형태로 사용해야 함
- scan 결과 후처리가 필요하면 L2 가 scan → synth 데이터를 전달 (synth 가
  scan 을 직접 import 하지 않음)
"""

__all__: list[str] = []
