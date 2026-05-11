"""gather 데이터 변환 계층 — 수정주가 / 기술 지표 dispatch.

수집 후 가공 단계 모듈. 호출자는 명시 path 사용:
    from dartlab.gather.transforms.adjustPrice import applyAdjustment, detectEventsFromPrices
    from dartlab.gather.transforms.indicatorDispatch import addIndicators, computeIndicator

facade re-export 하지 않는다 (alias 금지 룰).
"""
