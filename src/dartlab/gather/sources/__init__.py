"""gather 도메인 source facade — 시장별 fallback 체인 + 단일 도메인 수집.

각 모듈은 비동기 fetch() 함수를 export. Gather 클래스 (gather/__init__.py) 가
이 facade 들을 묶어 동기 메서드로 노출.

호출자는 명시 path 사용:
    from dartlab.gather.sources.price import fetch as fetchPrice
    from dartlab.gather.sources.news import toDataFrame

facade re-export 하지 않는다 (alias 금지 룰).
"""
