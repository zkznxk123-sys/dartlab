# logger.info → logEvent 마이그레이션 가이드 (T1-1)

> dartlab 의 50+ `logger.info()` 호출을 structured `logEvent()` 로 점진 마이그레이션.
> 1.0.0 게이트: structured log 비율 ≥ 90 percent (T1-1 KPI 가중 40 percent).

---

## 마이그레이션 패턴

### Before (점진 마이그레이션 대상)

```python
from dartlab.core.logger import getLogger

_log = getLogger(__name__)
_log.info("[cyan]⬇ HF[/] %s (%s/%s)", label, HF_REPO, hfDir)
```

### After (structured logEvent)

```python
from dartlab.core.logger import logEvent

logEvent(
    "info",
    "hf_download_start",  # snake_case event 이름
    label=label,
    repo=HF_REPO,
    directory=hfDir,
)
```

---

## 우선순위 (50+ 호출 분류)

| 우선순위 | 대상 | 갯수 (추정) | 이유 |
|--------|------|------------|------|
| **P0 (즉시)** | core/memory escalation / core/cache eviction | ~10 | metrics workflow grep 가장 가치 |
| **P1 (Q3)** | gather sync 진입/완료 / Company.show 호출 시작 | ~15 | latency P50/P95 측정 입력 |
| **P2 (Q4)** | scan recipe 호출 / story compose 단계 | ~15 | 통계 시계열 |
| **P3 (1.0.0 전)** | env.py interactive prompt (Rich markup 보존 필요) | ~10 | UX 영향 검토 후 |

---

## 회피해야 할 패턴

### Rich markup 보존 필요

```python
# Rich markup ([cyan]/[/] 등) 가 사용자 화면 출력에 필요한 경우
_log.info("[cyan]⬇ HF[/] %s", label)
# → logEvent 마이그레이션 시 markup 손실. 별도 print() 분기 또는 console.print() 유지.
```

### CLI interactive prompt

```python
# core/env.py 의 setup interactive flow
_log.info(f"\n  ✓ {envKey} 이미 설정됨")
# → 사용자가 직접 보는 출력. logEvent 마이그레이션 부적합. console.print() 또는 print() 유지.
```

---

## 측정

```bash
# 현재 structured log 비율 (T1-1 KPI 가중 40 percent)
uv run python -X utf8 -c "
import re
from pathlib import Path
total = struct = 0
for p in Path('src/dartlab').rglob('*.py'):
    text = p.read_text(encoding='utf-8', errors='replace')
    total += len(re.findall(r'\.info\(', text))
    struct += len(re.findall(r'logEvent\(', text))
print(f'logger.info: {total}, logEvent: {struct}, ratio: {struct/(total+struct)*100:.1f}%')
"
```

---

## 관련

- [src/dartlab/core/logger.py](../src/dartlab/core/logger.py) — `logEvent` API (T1-1)
- [src/dartlab/core/memory.py](../src/dartlab/core/memory.py) — `profileCall` decorator (T3-4) 가 logEvent 자동 호출
- [TODO.md](../TODO.md) T1-1 트랙
- [`.github/workflows/metrics.yml`](../.github/workflows/metrics.yml) — T1-2 메트릭 수집
