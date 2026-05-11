"""gather 인프라 계층 — HTTP / 캐시 / 회로 차단기.

내부용. 외부 호출자는 `from dartlab.gather.infra.{http,cache,resilience} import ...`
경로로 명시 import. facade re-export 하지 않는다 (alias 금지 룰).
"""
