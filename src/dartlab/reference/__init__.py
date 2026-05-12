"""reference — L1.5 JSON 룩업 + 매핑 엔진.

정적 reference dataset (JSON) + 매핑 엔진 (BaseMapper 등). 현
dartlab.core.data (JSON 8 종) + dartlab.reference.mappers (코드 8 종) 이 본
위치로 이동 예정 (P-CORE B). 본 단계는 골격만.

룰 (operation.architecture SSOT):
- import OK: dartlab.core, dartlab.gather, dartlab.providers
- import 금지: dartlab.{scan, frame, synth} (L1.5 4 형제 cross 금지)
- 진입 조건: ≥ 2 분석엔진이 같은 형태로 사용해야 함
- 정적 자원 (가공 아닌 룩업) 이지만 분석엔진이 직접 보는 표면이라 L1.5 동거
"""

__all__: list[str] = []
