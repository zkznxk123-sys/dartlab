"""블로그 자동 발간 도구 (T12-3) — 3 카테고리 + 사용자 manual approve.

T12-3 트랙: 기존 credit-reports auto 발간 외에 corporate / quant /
industry 3 카테고리 추가. 자동 발간 PR 은 label `auto-blog` + 사용자 manual
approve 강행 (CLAUDE.md `feedback_finish_to_end_no_midstop` 정합).

카테고리:
    1. corporate-stories: 회사별 자동 generate (사용자 명시 종목 시)
    2. quant-recipes: recipe 신규 추가 시
    3. industry-maps: sector rotation 신호 시

실행::

    python -X utf8 blog/_scripts/autoBlogGenerate.py corporate-stories --code 005930
    python -X utf8 blog/_scripts/autoBlogGenerate.py quant-recipes --recipe foreignBuyMomentum
    python -X utf8 blog/_scripts/autoBlogGenerate.py industry-maps --sector 반도체

각 호출은 *draft markdown 파일 생성* + label `auto-blog` PR template 제안.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BLOG_ROOT = REPO_ROOT / "blog" / "posts"


CORPORATE_TEMPLATE = """---
title: "{code} {corpName} — {date} 분석"
date: {date}
category: corporate-stories
auto: true
tags: [{code}, corporate]
---

# {code} {corpName} — {date} 분석

## 개요

TODO — dartlab.Story("{code}") 8 막 인과 결과.

## 재무 핵심

TODO — dartlab.Company("{code}").show("IS") + ratios.

## 의사결정

TODO — 위험 / 기회 / 모니터링 포인트.

## 데이터 ref

TODO — dartlab 의 원본 ref (재현 가능).
"""

QUANT_TEMPLATE = """---
title: "Quant recipe: {recipe}"
date: {date}
category: quant-recipes
auto: true
tags: [{recipe}, quant]
---

# Quant recipe: {recipe}

## 가설

TODO — recipe 가 포착하려는 시장 신호.

## 측정

TODO — factor 정의 + universe + lookback.

## 백테스트 결과

TODO — historical hit rate / Sharpe / drawdown.

## 운영 가이드

TODO — 신호 발화 시 의사결정 흐름.
"""

INDUSTRY_TEMPLATE = """---
title: "Industry rotation: {sector}"
date: {date}
category: industry-maps
auto: true
tags: [{sector}, industry]
---

# Industry rotation: {sector}

## 현재 regime

TODO — macro.cycle + sectorRotation.

## peer 매트릭스

TODO — industry.sectorMomentumLeadership.

## leader / laggard

TODO — Top 5 / Bottom 5.
"""


CATEGORY_HANDLERS: dict[str, str] = {
    "corporate-stories": CORPORATE_TEMPLATE,
    "quant-recipes": QUANT_TEMPLATE,
    "industry-maps": INDUSTRY_TEMPLATE,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="블로그 자동 발간 draft (T12-3)")
    parser.add_argument("category", choices=list(CATEGORY_HANDLERS.keys()))
    parser.add_argument("--code", help="회사 종목코드 (corporate-stories)")
    parser.add_argument("--corp-name", default="(corp name TBD)", help="회사 한글명")
    parser.add_argument("--recipe", help="quant recipe 이름 (quant-recipes)")
    parser.add_argument("--sector", help="섹터 이름 (industry-maps)")
    parser.add_argument("--out-dir", type=Path, default=BLOG_ROOT, help="블로그 posts root")
    args = parser.parse_args()

    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    template = CATEGORY_HANDLERS[args.category]

    if args.category == "corporate-stories":
        if not args.code:
            print("[autoBlog] corporate-stories 는 --code 필수")
            return 1
        body = template.format(code=args.code, corpName=args.corp_name, date=today)
        outFile = args.out_dir / args.category / f"{today}-{args.code}.md"
    elif args.category == "quant-recipes":
        if not args.recipe:
            print("[autoBlog] quant-recipes 는 --recipe 필수")
            return 1
        body = template.format(recipe=args.recipe, date=today)
        outFile = args.out_dir / args.category / f"{today}-{args.recipe}.md"
    elif args.category == "industry-maps":
        if not args.sector:
            print("[autoBlog] industry-maps 는 --sector 필수")
            return 1
        body = template.format(sector=args.sector, date=today)
        outFile = args.out_dir / args.category / f"{today}-{args.sector}.md"
    else:
        print(f"[autoBlog] 알 수 없는 카테고리 {args.category}")
        return 1

    outFile.parent.mkdir(parents=True, exist_ok=True)
    outFile.write_text(body, encoding="utf-8")
    print(f"[autoBlog] draft 생성: {outFile.relative_to(REPO_ROOT)}")
    print("[autoBlog] 다음 단계: TODO 채우기 + git commit -o + PR label 'auto-blog' + 사용자 manual approve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
