"""panel 셀 세분화 가능성 — 다각도 실측 테스트 (Phase 2 사전조사, 구현 아님).

정부 XBRL TE 셀(ACODE/ACONTEXT)이 재무3표뿐 아니라 **주석(NT_*)까지** 기계가독으로
세분화 가능한지 6 각도로 검증한다. 모든 수치는 005930 raw zip 실측 (추측 0).

각도:
    A. 주석 vs 재무 셀 커버리지 — NT_* 표가 ACODE/ACONTEXT 를 얼마나 박고 있나.
    B. ACONTEXT 결정론적 분해 — period + [(axis, member)...] 문법이 100% 성립하나.
    C. 차원 큐브 깊이 — 축이 몇 단까지 가나, distinct member 규모.
    D. 실제 주석표 라운드트립 — 한 NT_ 표를 (개념×기간) 격자로 펴서 값 복원.
    E. narrative-only 주석 식별 — TE 없는 서술형 주석은 contentRaw 텍스트로 남는가.
    F. 양식 robustness — 2023Q4 옛 보고서도 같은 문법인가.

실행: uv run python -X utf8 tests/_attempts/panelCellFeasibility.py

실측 결과 (005930, 2026-06-01):
    A 커버리지 — 주석(NT_*) 9,261 TE 중 6,166 개념셀·4,595 ctx셀·**503 distinct 개념**
        (재무3표 142 개념의 3.5배). 주석이 셀 세분화의 본진. 서술형 9표 제외 표주석 57개.
    B 분해 — ACONTEXT 5,704 전건 period 분해 **OK=5704 FAIL=0 (문법 100% 결정론)**.
        period = (C|P|BP)FY####(d|e)FY = 당기/전기/전전기 × duration(흐름)/instant(시점).
    C 큐브 — 축 깊이 1~6 (깊이2 최빈 3,805). distinct 축 52·멤버 309.
        모든 셀 Consolidated/Separate 기본축 + 자산클래스·자본구성·특수관계자 중첩.
    D 라운드트립 — 「8.재고자산(연결)」NT_C_D826380 → (개념×축) 16행 완전 복원.
        Gross/Allowance/net 3단, 당기·전기 값 정확. **무손실 round-trip 증명.**
    E 혼합모델 — 표주석 57(세분화) + 서술형 9(R4 contentRaw 텍스트 유지). 깔끔 분리.
    F 경계조건 (★중대) — ACONTEXT 도입 = **2025-03-11 사업보고서부터** (42 zip 전수).
        ACLASS 는 2017-03 부터지만 셀 ACONTEXT 는 최근 6개 공시만 (1016→5704 점증 ramp).
        → 셀 세분화는 **2025-03+ 기간만** 가능. 그 이전은 TABLE-GROUP(spine) 식별만,
        셀 내부는 contentRaw blob 유지. panel = 최신앵커 격자라 era 별 graceful 저하 정합.

가능성 결론: 주석까지 셀 세분화 **기술적으로 완전 가능** (100% 결정론·무손실 복원).
    단 시간 경계 = 2025-03+. wide 격자 불변, 행 깊이만 추가 (개념@축 → 행, period 열 재사용).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree

_TMP = Path.home() / "AppData" / "Local" / "Temp"
NEW = _TMP / "panelcell" / "20260310002820.xml"  # FY2025 사업보고서
OLD = _TMP / "panelold" / "20230307000542.xml"  # FY2022 사업보고서

_XBRL = "{XBRL}"


def _strip(aclass: str) -> str:
    return aclass[len(_XBRL) :] if aclass.startswith(_XBRL) else aclass


def _classify(rawId: str) -> str:
    if rawId.startswith("NT_"):
        return "주석(NT_*)"
    if rawId.split("_")[0] in {"BS", "IS", "CF", "EF"} or rawId[:2] in {"BS", "IS", "CF", "EF"}:
        return "재무(BS/IS/CF/EF)"
    return f"기타({rawId.split('_')[0]})"


def _parse(path: Path):
    parser = etree.XMLParser(recover=True, huge_tree=True)
    return etree.fromstring(path.read_bytes(), parser)


def _nearestGroup(te):
    """TE 셀이 속한 가장 가까운 ancestor TABLE-GROUP 의 ACLASS(strip)."""
    p = te.getparent()
    while p is not None:
        if p.tag == "TABLE-GROUP":
            ac = (p.get("ACLASS", "") or "").strip()
            if ac:
                return _strip(ac)
        p = p.getparent()
    return None


def _decodeContext(ctx: str):
    """ACONTEXT → (periodToken, [(axis, member)...]). 결정론적 분해."""
    parts = ctx.split("_")
    period = parts[0]  # CFY2025eFY / PFY2024dFY / BPFY2023eFY ...
    rest = parts[1:]
    # axis/member 는 'ifrs-full'|'dart'|'entityNNNN' prefix 로 토큰화돼 '_' 로 잘림 → 재조합
    tokens = []
    buf = []
    for seg in rest:
        if seg in ("ifrs-full", "dart") or seg.startswith("entity"):
            if buf:
                tokens.append("_".join(buf))
            buf = [seg]
        else:
            buf.append(seg)
    if buf:
        tokens.append("_".join(buf))
    # Axis 로 끝나는 토큰 = 축, Member 로 끝나는 토큰 = 멤버
    pairs = []
    curAxis = None
    for t in tokens:
        if t.endswith("Axis"):
            curAxis = t
        elif t.endswith("Member"):
            pairs.append((curAxis, t))
            curAxis = None
    return period, pairs


def angleAB_coverage_and_context(root, label: str):
    print(f"\n{'=' * 70}\n[{label}] 각도 A·B — 주석 커버리지 + ACONTEXT 분해\n{'=' * 70}")
    byClass = defaultdict(lambda: {"te": 0, "concept": 0, "ctx": 0, "concepts": set()})
    ctxDecodeOk = 0
    ctxDecodeFail = 0
    periodTokens = Counter()
    for te in root.iter("TE"):
        grp = _nearestGroup(te)
        if grp is None:
            continue
        kind = _classify(grp)
        byClass[kind]["te"] += 1
        acode = (te.get("ACODE", "") or "").strip()
        actx = (te.get("ACONTEXT", "") or "").strip()
        if acode.startswith(("ifrs-full_", "dart_", "entity")):
            byClass[kind]["concept"] += 1
            byClass[kind]["concepts"].add(acode)
        if actx:
            byClass[kind]["ctx"] += 1
            period, pairs = _decodeContext(actx)
            periodTokens[period] += 1
            # 분해 검증: period 토큰이 (C|P|BP)FY####(d|e)FY 형태인가
            if re.fullmatch(r"(B?P?C?FY\d{4}[de]FY|FY\d{4}[de]FY)", period) or re.match(r"^[A-Z]+FY\d{4}", period):
                ctxDecodeOk += 1
            else:
                ctxDecodeFail += 1
    print(f"{'분류':<22}{'TE셀':>8}{'개념셀':>8}{'ctx셀':>8}{'distinct개념':>12}")
    for kind, d in sorted(byClass.items()):
        print(f"{kind:<22}{d['te']:>8}{d['concept']:>8}{d['ctx']:>8}{len(d['concepts']):>12}")
    print(f"\nACONTEXT period 분해: OK={ctxDecodeOk}  FAIL={ctxDecodeFail}  (FAIL=0 이면 문법 100%)")
    print("period 토큰 분포:", dict(periodTokens.most_common()))
    return byClass


def angleC_cube_depth(root, label: str):
    print(f"\n{'=' * 70}\n[{label}] 각도 C — 차원 큐브 깊이\n{'=' * 70}")
    depths = Counter()
    axes = Counter()
    members = set()
    for te in root.iter("TE"):
        actx = (te.get("ACONTEXT", "") or "").strip()
        if not actx:
            continue
        _, pairs = _decodeContext(actx)
        depths[len(pairs)] += 1
        for ax, mem in pairs:
            axes[ax] += 1
            members.add(mem)
    print("축 깊이 분포 (멤버쌍 개수 → 셀수):", dict(sorted(depths.items())))
    print(f"distinct 축(Axis): {len(axes)}  distinct 멤버: {len(members)}")
    print("상위 축:")
    for ax, n in axes.most_common(8):
        print(f"  {n:5d}  {ax}")


def angleD_roundtrip(root, label: str):
    print(f"\n{'=' * 70}\n[{label}] 각도 D — 실제 주석표 라운드트립 (개념×기간 격자 복원)\n{'=' * 70}")
    # 재고자산 주석(NT_ 중 InventoriesMember/Inventories 개념 보유 표) 탐색
    target = None
    for tg in root.iter("TABLE-GROUP"):
        ac = _strip((tg.get("ACLASS", "") or "").strip())
        if not ac.startswith("NT_"):
            continue
        codes = [te.get("ACODE", "") for te in tg.iter("TE") if te.get("ACONTEXT")]
        if any("Inventor" in c for c in codes):
            target = (ac, tg)
            break
    if target is None:
        print("재고 주석표 미발견 — 첫 ACONTEXT 보유 NT_ 표로 대체")
        for tg in root.iter("TABLE-GROUP"):
            ac = _strip((tg.get("ACLASS", "") or "").strip())
            if ac.startswith("NT_") and any(te.get("ACONTEXT") for te in tg.iter("TE")):
                target = (ac, tg)
                break
    if target is None:
        print("ACONTEXT 보유 주석표 없음")
        return
    ac, tg = target
    title = tg.find("./TITLE")
    titleTxt = "".join(title.itertext()).strip() if title is not None else ""
    print(f"표: {ac}  «{titleTxt[:50]}»")
    grid = defaultdict(dict)  # (concept, axisPath) -> {period: value}
    for te in tg.iter("TE"):
        acode = (te.get("ACODE", "") or "").strip()
        actx = (te.get("ACONTEXT", "") or "").strip()
        if not (acode.startswith(("ifrs-full_", "dart_")) and actx):
            continue
        period, pairs = _decodeContext(actx)
        axisPath = "|".join(m for _, m in pairs) or "—"
        val = re.sub(r"<[^>]+>", "", etree.tostring(te, encoding="unicode")).strip()
        grid[(acode, axisPath)][period] = val
    print(f"복원된 (개념×축) 행: {len(grid)}")
    for (acode, axisPath), periods in list(grid.items())[:8]:
        short = acode.replace("ifrs-full_", "").replace("dart_", "")
        ax = axisPath.replace("ifrs-full_", "").replace("dart_", "")[:40]
        print(f"  {short:<32} [{ax:<40}] {periods}")


def angleE_narrative(root, label: str):
    print(f"\n{'=' * 70}\n[{label}] 각도 E — narrative-only 주석 식별\n{'=' * 70}")
    tableNotes = 0
    narrNotes = 0
    for tg in root.iter("TABLE-GROUP"):
        ac = _strip((tg.get("ACLASS", "") or "").strip())
        if not ac.startswith("NT_"):
            continue
        hasCtx = any(te.get("ACONTEXT") for te in tg.iter("TE"))
        if hasCtx:
            tableNotes += 1
        else:
            narrNotes += 1
    print(f"주석 표(ACONTEXT 보유, 셀 세분화 대상): {tableNotes}")
    print(f"주석 서술형(ACONTEXT 0, contentRaw 텍스트 유지): {narrNotes}")
    print("→ 세분화는 표 주석만, 서술형은 R4 contentRaw 그대로 (혼합 모델 가능)")


if __name__ == "__main__":
    newRoot = _parse(NEW)
    angleAB_coverage_and_context(newRoot, "신양식 FY2025")
    angleC_cube_depth(newRoot, "신양식 FY2025")
    angleD_roundtrip(newRoot, "신양식 FY2025")
    angleE_narrative(newRoot, "신양식 FY2025")
    if OLD.exists():
        oldRoot = _parse(OLD)
        print(f"\n\n{'#' * 70}\n# 각도 F — 양식 robustness (2023Q4 옛 보고서)\n{'#' * 70}")
        angleAB_coverage_and_context(oldRoot, "옛양식 FY2022")
        angleC_cube_depth(oldRoot, "옛양식 FY2022")
