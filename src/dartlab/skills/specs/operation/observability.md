---
id: operation.observability
title: Observability — logging / tracing 표준
kind: curated
scope: builtin
status: drafted
category: operation
purpose: dartlab 운영 observability 표준 — logging level / structured logs / tracing span / metric emission. CLAUDE.md "디버그는 stdout, 파일은 /tmp/" 룰의 production 확장.
whenToUse:
  - observability
  - logging
  - tracing
  - structured logs
  - metric emission
inputs:
  - 운영 컨텍스트 (server / batch / CLI)
outputs:
  - log stream
  - trace span
  - metric
toolRefs: []
knowledgeRefs:
  - operation.code
sourceRefs:
  - dartlab://skills/operation.observability
requiredEvidence:
  - skillRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
linkedSkills:
  - operation.code
---

## 3 layer

### 1. logging

```python
import logging
logger = logging.getLogger("dartlab")
logger.info("axis %s computed for %s in %.3fs", axis, target, elapsed)
```

- level: DEBUG / INFO / WARN / ERROR / CRITICAL.
- production INFO + 위 / dev DEBUG.
- 구조화 (key=value 또는 JSON).

### 2. tracing (옵션)

OpenTelemetry 호환 span 추가 가능 (server 측 한정):

```python
from opentelemetry import trace
tracer = trace.get_tracer("dartlab")
with tracer.start_as_current_span("Company.panel", attributes={"target": "005930"}):
    ...
```

### 3. metric

- cache hit/miss (`runtime.cacheStrategy`)
- per-axis latency (p50/p95/p99)
- error rate (per-axis)
- heap usage (Polars Rust)

## 강행 룰

1. CLI 모드: stdout 직접 (CLAUDE.md 룰).
2. server 모드: structured logs + 옵션 tracing.
3. 비밀 키 / API key 로그 금지.
4. 사용자 입력 echo 금지 (PII).

## 안티패턴

- print() 무차별 사용 (CLI 외).
- log level WARN 이상 무차별 (signal-to-noise ↓).
- exception 시 stack trace 없는 단순 INFO log.

## 기본 검증

- structured logs JSON parsable.
- tracing span 의 attribute 일관 (`target`, `axis`, `period`).
- metric emit endpoint 정합.
