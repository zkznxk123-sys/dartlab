"""gather 도메인-지표 매핑 계층.

종목/제품 → 거시지표 매핑 SSOT. 호출자는 명시 path 사용:
    from dartlab.gather.mapping.exogenousAxes import ExogenousIndicator, getExogenousIndicators
    from dartlab.gather.mapping.productIndicators import PRODUCT_INDICATOR_MAP

facade re-export 하지 않는다 (alias 금지 룰).
"""
