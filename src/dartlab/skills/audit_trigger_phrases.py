"""Trigger phrase audit script — Scope 4.

각 SKILL.md / recipe.md 의 `purpose:` 끝에 "트리거: '...', '...'." 한 문장을 추가한다.
이미 트리거 문구가 있으면 skip. lastUpdated 도 함께 갱신.

operation.extendSkills "Trigger phrase 작성 규칙" 참조.

사용:
    uv run python -X utf8 src/dartlab/skills/audit_trigger_phrases.py [--dry-run]

로컬 dev 도구. CI 비포함. 실행 후 git diff 로 검토.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "skills" / "specs"
TODAY = "2026-05-07"
# YAML frontmatter 에서 mid-value colon 은 nested mapping 으로 해석돼 ScannerError 발생.
# 따라서 "트리거:" 대신 em dash "트리거 —" 사용. detect 시 두 패턴 모두 인식.
TRIGGER_TOKEN_DETECT = re.compile(r"트리거\s*[—:\-]")
TRIGGER_PREFIX = "트리거 —"

# {file_stem: "trigger phrase string (no leading 트리거:, no trailing period)"}
ENGINE_TRIGGERS: dict[str, str] = {
    "analysis": "'재무 분석', '가치평가', '지배구조 점검', '전망'",
    "company": "'회사 분석', '단일 기업', '005930', 'Company.show'",
    "credit": "'신용 분석', '부도 위험', '신용등급', 'dCR'",
    "dashboard": "'회사 스냅샷', '종합 한눈에', 'dashboard'",
    "data": "'데이터 다운로드', '데이터 수집', 'data 명세'",
    "edgar": "'미국 공시', '10-K', 'SEC', 'EDGAR'",
    "gather": "'가격', '뉴스', '소유구조', '컨센서스', '외부 데이터 수집'",
    "industry": "'산업 분석', '섹터', '업종', 'industry'",
    "macro": "'매크로', '거시', '금리', '환율'",
    "mappers": "'항목 매핑', '컬럼 정규화', 'snake_id 변환'",
    "quant": "'퀀트', '팩터', '백테스트', '모멘텀', '기술적 신호'",
    "scan": "'스캔', '종목 발굴', '후보 추출', '랭킹'",
    "search": "'종목 검색', '회사명 검색' (AI 사용 비권장 — index 신선도 부족)",
    "story": "'보고서', '기업 이야기', 'story', '6 막 인과'",
    "viz": "'시각화', '차트', '표 시각화', 'compile_visual'",
}

RECIPE_TRIGGERS: dict[str, str] = {
    "capitalAllocationScorecard": "'자본배분 평가', 'FCF 사용처', 'ROIIC', 'Buffett 자본배분'",
    "companyDeepAnalysis": "'기업 깊이 분석', '6 막 종합', '단일 종목 deep dive'",
    "compounderCandidates": "'compounder 발굴', 'quality 일관 종목', 'Buffett 스타일 횡단'",
    "creditDeepDive": "'신용 깊이 분석', '단일 회사 신용', '부도 위험 종합'",
    "creditDistressDual": "'Altman + Ohlson', '부도 위험 2 모델 합의', 'Z-Score O-Score'",
    "dataAvailabilityFirst": "'데이터 있나 확인', '분석 전 데이터 점검', '수집 누락 체크'",
    "debtStructureAudit": "'부채 구조 audit', '만기 분포', '이자보상배율', '신용 등급 횡단'",
    "disclosureEvent": "'최근 공시', '신규 공시 영향', '공시 본문 변화', 'thesis 영향 평가'",
    "disclosureRiskScreen": "'공시 위험 스캔', '정정 빈도 횡단', '공시 위험 후보'",
    "distressFilter": "'부도 위험 필터', 'Altman Z 횡단', '블랙리스트', '회피 절차'",
    "dividendThesis": "'배당 매력도', '배당 정책', '배당 thesis'",
    "dupontDriver": "'ROE 분해', 'DuPont 5 동인', 'ROE 추적'",
    "earningsQualityCheck": "'이익 quality 점검', '발생주의 vs 현금흐름', '일회성 비중'",
    "earningsQualityTriad": "'Sloan accruals', 'Beneish M-Score', 'Novy-Marx GP/A', '이익 quality 3 모델'",
    "esgGovernanceLight": "'ESG light', '거버넌스 audit', 'ESG 데이터 부재 시'",
    "financialStatementCompare": "'재무제표 비교', '두 회사 차이', '회사 간 비교'",
    "flowAndPattern": "'수급', '외인 기관 매매', '차트 패턴', '단기 entry/exit'",
    "garpScreen": "'GARP', 'PEG', 'Lynch 성장가치', 'PEG ≤ 1'",
    "governanceAudit": "'지배구조 위험', '이사회 독립성', '감사 신호', '분식 가능성'",
    "grahamDeepValue": "'Graham deep value', '안전마진', 'chaebol discount 회피'",
    "growthScreenToDeepDive": "'성장 스캔 후 깊이 분석', '상위 N 깊이 분석'",
    "industryDeepDive": "'산업 깊이 분석', '가치 사슬', '핵심 종목', '업종 분석'",
    "insiderEventCheck": "'내부자 거래', '임원 변경', '자본변동 이벤트'",
    "intrinsicValueBand": "'본질가치 band', 'Graham + EVA + CFROI', 'fair value 3 anchor'",
    "inventoryAndCycle": "'재고 사이클', '회전 진단', '반도체/석유화학 사이클'",
    "leverageSensitivity": "'영업레버리지', '재무레버리지', 'DOL DFL DCL', '매크로 충격 민감도'",
    "macroLiquidityCycle": "'매크로 유동성', '금리 환율 위기 신호', '거시 사이클'",
    "macroToCompany": "'매크로 → 회사 전이', '금리 환율 회사 영향', '단계별 추적'",
    "peerBenchmark": "'peer 비교', '동종 5~10 종 벤치마크', 'ratio 4 축'",
    "piotroskiLite": "'F-Score', 'Piotroski 7 항목', '저평가 우량 발굴'",
    "qualityValueScreen": "'gross profitability', 'Novy-Marx 2013', 'quality value 횡단'",
    "quantTechnicalReview": "'기술적 신호', '모멘텀 변동성', '차트 패턴 4 축'",
    "scenarioAnalysis": "'base/bull/bear', '3 시나리오', '시장 regime', '불확실성 정량화'",
    "screenAndChart": "'스캔 후 차트', 'table-backed chart', '보고서 직전 시각화'",
    "sectorRotation": "'섹터 로테이션', '업종 순환', '경기 사이클별 섹터'",
    "smallCapDiscovery": "'중소형주 발굴', 'small cap discovery', '소외 종목'",
    "storyReportBuild": "'보고서 작성', '기업 이야기 조립', 'story 빌드'",
    "usMarketReview": "'미국 시장 점검', 'US market review', 'EDGAR 분기'",
    "usageAndApi": "'사용법 안내', 'API 도움말', 'dartlab 호출 예시'",
    "valuationBandTrack": "'밸류에이션 band 추적', '시계열 valuation', '멀티플 변천'",
    "valuationCheck": "'밸류에이션 점검', 'fair value', '저평가 판단'",
    "workforceAndCapital": "'인력 자본', '종업원 신호', 'workforce'",
    "workingCapitalQuality": "'운전자본 quality', '재고 매출채권', 'CCC 진단'",
}


def update_purpose(text: str, trigger_phrase: str) -> tuple[str, bool]:
    """purpose: 라인에 트리거 문구를 append. 이미 있으면 (이전 colon 형태 포함) 정정/skip."""
    pattern = re.compile(r"^(purpose:\s*.+)$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return text, False
    purpose_line = match.group(1)
    has_trigger = bool(TRIGGER_TOKEN_DETECT.search(purpose_line))
    if has_trigger:
        # 이전에 "트리거:" 로 박혀 YAML 깨진 형태가 있으면 "트리거 —" 로 교체.
        if "트리거:" in purpose_line:
            new_line = purpose_line.replace("트리거:", TRIGGER_PREFIX)
            new_text = text[: match.start(1)] + new_line + text[match.end(1) :]
            return new_text, True
        return text, False
    # 끝에 . 있으면 그 안쪽에 합쳐 붙임. 없으면 . 추가.
    stripped = purpose_line.rstrip()
    if stripped.endswith("."):
        new_line = f"{stripped} {TRIGGER_PREFIX} {trigger_phrase}."
    else:
        new_line = f"{stripped}. {TRIGGER_PREFIX} {trigger_phrase}."
    new_text = text[: match.start(1)] + new_line + text[match.end(1) :]
    return new_text, True


def update_last_updated(text: str) -> str:
    pattern = re.compile(r"^(lastUpdated:\s*['\"]?)([^'\"\n]+)(['\"]?)$", re.MULTILINE)
    return pattern.sub(rf"\g<1>{TODAY}\g<3>", text)


def process_file(path: Path, trigger_phrase: str, dry_run: bool) -> str:
    original = path.read_text(encoding="utf-8")
    new_text, changed = update_purpose(original, trigger_phrase)
    if not changed:
        return "skip"
    new_text = update_last_updated(new_text)
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return "updated"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    counts = {"updated": 0, "skip": 0, "missing": 0}

    # 16 engine SKILL.md
    for engine, trigger in ENGINE_TRIGGERS.items():
        path = ROOT / "engines" / engine / "SKILL.md"
        if not path.exists():
            print(f"[missing] {path}")
            counts["missing"] += 1
            continue
        result = process_file(path, trigger, dry_run)
        print(f"[{result}] {path.relative_to(ROOT.parent)}")
        counts[result] += 1

    # 43 recipes
    for stem, trigger in RECIPE_TRIGGERS.items():
        path = ROOT / "engines" / "recipe" / f"{stem}.md"
        if not path.exists():
            print(f"[missing] {path}")
            counts["missing"] += 1
            continue
        result = process_file(path, trigger, dry_run)
        print(f"[{result}] {path.relative_to(ROOT.parent)}")
        counts[result] += 1

    print(
        f"\n총 {sum(counts.values())} 파일: updated={counts['updated']} skip={counts['skip']} missing={counts['missing']}"
    )
    if dry_run:
        print("(dry-run — 파일 변경 없음)")
    return 0 if counts["missing"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
