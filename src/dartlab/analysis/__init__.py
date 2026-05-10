"""Analysis 엔진 — L2 분석 모듈 통합.

하위 모듈:
- financial: 재무제표 분석 (14축 본체 + 인사이트 + 리서치)
- forecast: 전망분석 (추정, 시뮬레이션)
- valuation: 가치평가

Guide:
    AI 역할: AI는 analysis를 단일 기업 재무·가치·리스크 해석 엔진으로 보고 axis/subaxis와 필요한 재무 evidence를 선택한다.

진입점 패턴: ``Company.analysis(axis)`` 또는 sub-module (``analysis.financial`` ·
``analysis.valuation`` 등) 직접 import.
"""

# Public surface — sub-module 진입점만. Engine class 자체는 없고 Company.analysis() 메서드 사용.
__all__: list[str] = []
