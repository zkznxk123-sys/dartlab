"""dartlab observability sidecars — ledger·계수 추적 (옵트인).

본 패키지는 prod 동작 0 영향. 모든 모듈은 ENV gate (`DARTLAB_*`) 로
기본 OFF. nightly prebuild/audit job 또는 운영자 의지로만 활성.

Capabilities:
    - 매핑 미커버 계정 관측 ledger (mapping_ledger).

Guide:
    - 일반 사용자 API 아님. pivot/scan 내부에서만 호출.

AIContext:
    - 본 패키지의 모든 함수는 함수 시그니처와 ENV 조건이 docstring 의
      Args/Example 에 명시된 대로만 호출.
"""
