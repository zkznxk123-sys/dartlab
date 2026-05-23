"""lru_cache hit-rate 측정 — textStructure.py 6 사이트.

`pipeline.sections(code)` 호출 후 각 lru_cache 의 hit/miss/maxsize/currsize 출력.
다종목 batch 시 누적 패턴 확인용 — 005930 / 000660 / 005380 3 종 순차 호출.

결과 (2026-05-23, 3 종목 sequential, disk cache bypass):

옛 maxsize (Phase 1.3 이전):
    _normalizeHeadingText  hits= 47025  misses= 2593  size= 2593/16384  hit%=94.8
    _headingKey            hits= 43904  misses= 2579  size= 2579/16384  hit%=94.5
    _semanticSegmentKey    hits= 43478  misses= 3005  size= 3005/16384  hit%=93.5
    _isTemporalMarker      hits=    17  misses=  556  size=  512/  512  hit%= 3.0
    _bodyAnchor            hits= 25791  misses=19888  size=19888/32768  hit%=56.5
    _detectHeading         hits=210361  misses=48230  size=48230/65536  hit%=81.3

신 maxsize (Phase 1.3 — 78% 축소):
    _normalizeHeadingText  hits= 47052  misses= 2593  size= 2593/ 4096  hit%=94.8
    _headingKey            hits= 43904  misses= 2579  size= 2579/ 4096  hit%=94.5
    _semanticSegmentKey    hits= 43478  misses= 3005  size= 3005/ 4096  hit%=93.5
    _isTemporalMarker      (no cache — hit% 3 였던 캐시 제거)
    _bodyAnchor            hits= 25753  misses=19926  size= 8192/ 8192  hit%=56.4
    _detectHeading         hits=209849  misses=48742  size=16384/16384  hit%=81.2

결론: maxsize 163,232 → 36,608 (78% 감축) 후에도 hit rate 변화 < 0.1%p — LRU 가
hot-path 우선 유지하여 cap 작아도 효과 보존. 메모리 ~18 MB 절감 추정.
"""

from __future__ import annotations

import sys

from dartlab.providers.dart.docs.sections import diskCache, textStructure
from dartlab.providers.dart.docs.sections.pipeline import sections

# disk cache bypass — 진짜 build path 측정용. 함수 monkeypatch.
diskCache.loadDiskCache = lambda *args, **kwargs: None  # type: ignore[assignment]
diskCache.saveDiskCache = lambda *args, **kwargs: None  # type: ignore[assignment]


def _printInfo(name: str, fn) -> None:
    if not hasattr(fn, "cache_info"):
        print(f"{name:30s}  (no cache)", flush=True)
        return
    info = fn.cache_info()
    total = info.hits + info.misses
    rate = (info.hits / total * 100.0) if total > 0 else 0.0
    print(
        f"{name:30s}  hits={info.hits:7d}  misses={info.misses:7d}  "
        f"size={info.currsize:5d}/{info.maxsize:6d}  hit%={rate:5.1f}",
        flush=True,
    )


def main(codes: list[str]) -> None:
    for code in codes:
        print(f"\n=== sections({code}) ===", flush=True)
        result = sections(code)
        print(f"  rows={result.height if result is not None else 0}", flush=True)

    print("\n=== lru_cache stats (누적) ===", flush=True)
    for name in (
        "_normalizeHeadingText",
        "_headingKey",
        "_semanticSegmentKey",
        "_isTemporalMarker",
        "_bodyAnchor",
        "_detectHeading",
    ):
        fn = getattr(textStructure, name)
        _printInfo(name, fn)


if __name__ == "__main__":
    codes = sys.argv[1:] or ["005930", "000660", "005380"]
    main(codes)
