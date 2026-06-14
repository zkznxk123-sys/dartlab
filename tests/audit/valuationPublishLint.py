"""발간 표면 한정 투자권유 금지어 lint guard (시뮬레이터 가치평가 보고서).

시나리오 시뮬레이터 가치평가 보고서(`reportType: simulation`)는 무료 공개 발간이라
규제선(투자권유·단일 목표가·매수/매도 rating)을 *기계 강제*로 차단해야 한다
(PRD 08-valuation-report.md §2.2·§7, 09 §10.1 fatal①). 본 guard 가 그 lint 이다.

★스캔 표면 한정 (핵심 — leaf CI red 회피):
    스캔 대상은 *발간 표면*(frontmatter ``reportType: simulation`` 마크다운)뿐이다.
    src `.py` 는 영원히 스캔하지 않는다 — `analysis/valuation/priceImplied.py` 의
    ``signal="underpriced"`` 같은 leaf 의 *정당한* 금지어 사용을 잡으면 CI red 이므로,
    발간 출력(사용자가 읽는 마크다운)만 검사한다. `_isSimulationReport()` 가 그 게이트.

★스켈레톤-now, active-on-surface:
    현재 발간 표면(`reportType: simulation` 파일)은 0건이라 본 lint 는 green no-op 다
    (T2 발간 표면 신설 = PRD 09 §10.1 T2, 엔진 코어 졸업 후 별도 phase). 발간 표면이
    ship 되는 순간(publisher 가 ``reportType: "simulation"`` frontmatter 를 emit) 본
    lint 가 자동 발화한다 — 코드 수정 0. T1↔T2 자동발화 계약(09 §10.1 FIX-2):
    `_isSimulationReport` 매치 키는 publisher emit 키와 바이트 동일이어야 한다.

검사(발간 표면 한정):
    1. 매수/매도 rating (한/영) — "매수의견"/"매도의견"/"strong buy"/"strong sell" 등.
    2. ``underpriced``/``overpriced`` 누출 → "consistent/optimistic/pessimistic" 로 표기.
    3. 단일 목표가(범위 비동반) — "목표주가 NNNNN원" 식 점추정.
    4. 예상수익률 약속 — "예상 수익률 NN%" 식 확정 어휘.
    5. 개인화 추천 — "당신의 상황에서"/"귀하의 포트폴리오"/"회원님" 등 개별 적응 어휘.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ★발간 표면만 — src 미포함(leaf 의 정당한 금지어 사용을 안 잡음 = CI red 0)
SURFACE_ROOTS: tuple[Path, ...] = (REPO_ROOT / "blog" / "05-company-reports",)

# ★publisher emit 키와 바이트 동일이어야 자동발화(09 §10.1 FIX-2)
_SIMULATION_FRONTMATTER = re.compile(r"""^reportType:\s*["']?simulation["']?\s*$""")

# 금지어 패턴 → (정규식, 사유+대체어휘). PRD 08 §7 ①~④ 도출.
_BANNED: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"매[수도]\s*의견|적극\s*매수|비중\s*(?:확대|축소)"),
        "매수/매도 rating 금지 — 조건부 분류(consistent/optimistic/pessimistic)로",
    ),
    (
        re.compile(r"(?i)\bstrong[\s_]?(?:buy|sell)\b|\b(?:buy|sell)\s+rating\b"),
        "buy/sell rating 금지 — rating 아닌 조건부 진술",
    ),
    (
        re.compile(r"(?i)\b(?:underpriced|overpriced)\b"),
        "underpriced/overpriced 누출 금지 — consistent/optimistic/pessimistic 로 표기",
    ),
    (
        re.compile(r"목표\s*주가\s*[0-9,]+\s*원"),
        "단일 목표가(점추정) 금지 — P10/P50/P90 범위 + reverseDCF 닻 동반",
    ),
    (
        re.compile(r"예상\s*수익률\s*[0-9.]+\s*%"),
        "예상수익률 약속 금지 — scenario≠forecast, 확정 어휘 불가",
    ),
    (
        re.compile(r"당신의?\s*(?:상황|포트폴리오|계좌|보유)|귀하의?\s*(?:상황|포트폴리오|계좌|보유)|회원님"),
        "개인화 추천 금지 — 개별 상황 적응은 Advisers Act 본체(impersonal 유지)",
    ),
)


def _isSimulationReport(md_path: Path) -> bool:
    """frontmatter ``reportType: simulation`` 매치 시에만 True (스캔 게이트).

    `.md` 가 아니거나 frontmatter 가 없으면 False. src `.py` 는 항상 False
    (leaf 의 정당한 금지어 사용을 스캔 대상에서 영원히 배제 = CI red 0 핵심).
    """
    if md_path.suffix != ".md" or not md_path.exists():
        return False
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return False
    # 두 번째 '---' 전까지가 frontmatter
    lines = text.splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if _SIMULATION_FRONTMATTER.match(line.strip()):
            return True
    return False


def _scanSurface(root: Path) -> list[tuple[Path, int, str, str]]:
    """발간 표면(simulation 보고서)만 수집 → (파일, 행, 위반어, 사유)."""
    violations: list[tuple[Path, int, str, str]] = []
    if not root.exists():
        return violations
    for md_path in sorted(root.rglob("*.md")):
        if not _isSimulationReport(md_path):
            continue
        for idx, line in enumerate(md_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pattern, reason in _BANNED:
                m = pattern.search(line)
                if m:
                    violations.append((md_path, idx, m.group(0), reason))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="위반 시 exit 1")
    args = parser.parse_args()

    all_violations: list[tuple[Path, int, str, str]] = []
    scanned = 0
    for root in SURFACE_ROOTS:
        if root.exists():
            scanned += sum(1 for p in root.rglob("*.md") if _isSimulationReport(p))
        all_violations.extend(_scanSurface(root))

    if all_violations:
        print(f"[FAIL] 발간 표면 투자권유 금지어 {len(all_violations)} 건:")
        for md_path, line_no, hit, reason in all_violations[:20]:
            rel = md_path.relative_to(REPO_ROOT)
            print(f"    {rel}:L{line_no} '{hit}' — {reason}")
    else:
        print(f"[OK] 발간 표면(simulation 보고서 {scanned}건) 투자권유 금지어 0 건")

    if args.strict and all_violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
