"""산업별 지표 사전 수집 → Parquet 캐시 (FRED 미국 산업지표 + 관세청 한국 수출).

PRODUCT_INDICATOR_MAP에 등록된 FRED 시리즈와 관세청 HS 품목을 수집해
~/.dartlab/cache/macro/{fred,customs}/ 에 Parquet으로 저장한다.

한 번 실행하면 calcMacroRegression이 캐시만 읽어서 산업 지표를 회귀 변수로 사용.
관세청 월별 수출은 미국 FRED 산업지표의 한국 실수출 대응물(산업 사이클 선행).

Usage:
    uv run python -X utf8 .github/scripts/sync/collectIndustryIndicators.py
"""

from __future__ import annotations

import os

# .env 로드
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def main():
    from dartlab.gather.fred import Fred
    from dartlab.gather.mapping.productIndicators import PRODUCT_INDICATOR_MAP
    from dartlab.gather.transforms.macro import enrichAndCache

    # 고유 FRED 시리즈 ID 추출
    fredIds: set[str] = set()
    for mapping in PRODUCT_INDICATOR_MAP.values():
        for sid in mapping.get("fred", []):
            fredIds.add(sid)

    print(f"[1/3] FRED 산업 지표 {len(fredIds)}개 수집 시작")

    fc = Fred()
    success = 0
    failed = 0

    for sid in sorted(fredIds):
        try:
            df = fc.series(sid, start="2000-01-01")
            if len(df) > 0:
                enriched = enrichAndCache(sid, df, source="fred")
                print(f"  OK  {sid:25s} {len(enriched):5d} rows ({enriched['date'][0]} ~ {enriched['date'][-1]})")
                success += 1
            else:
                print(f"  EMPTY {sid}")
                failed += 1
        except Exception as exc:
            print(f"  FAIL {sid}: {exc}")
            failed += 1

    fc.close()

    # ── 관세청 무역통계: HS 코드 월별 수출액 → 로컬 캐시 (source="customs") ──
    from dartlab.gather.customs import Customs

    customsIds: set[str] = set()
    for mapping in PRODUCT_INDICATOR_MAP.values():
        for hs in mapping.get("customs", []):
            customsIds.add(hs)

    print(f"\n[2/3] 관세청 무역통계 {len(customsIds)}개 HS 수집 시작")
    cc = Customs()
    for hs in sorted(customsIds):
        try:
            df = cc.series(hs)
            if len(df) > 0:
                enriched = enrichAndCache(hs, df, source="customs")
                print(f"  OK  HS {hs:23s} {len(enriched):5d} rows ({enriched['date'][0]} ~ {enriched['date'][-1]})")
                success += 1
            else:
                print(f"  EMPTY HS {hs}")
                failed += 1
        except Exception as exc:
            print(f"  FAIL HS {hs}: {exc}")
            failed += 1
    cc.close()

    print(f"\n[3/3] 완료: {success} 성공, {failed} 실패")


if __name__ == "__main__":
    main()
