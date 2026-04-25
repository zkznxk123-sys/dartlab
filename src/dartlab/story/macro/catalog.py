"""macro 보고서 블록 카탈로그 — 6막 인과 서사 구조.

story/catalog.py 패턴. 6막은 "앞 막이 뒷 막의 원인".

학술 근거:
    - FOMC 성명서 (고용/물가 → 정책 → 포워드 가이던스)
    - ECB 전파 메커니즘 (정책금리 → 금융상태 → 실물 → 물가)
    - Bernanke & Gertler (1995) — 신용 채널, 금융가속기
    - Ray Dalio — 단기/장기 부채 사이클
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroSectionMeta:
    """macro 보고서 섹션 메타데이터."""

    key: str
    partId: str
    title: str
    helper: str
    aiGuide: str


SECTIONS: list[MacroSectionMeta] = [
    MacroSectionMeta(
        "dashboard",
        "M0",
        "경제 신호등",
        "6막 전체 상태를 한눈에. 종합 점수 + 기여도.",
        "종합 점수와 기여도를 분석하고, 가장 주목할 축을 식별하라.",
    ),
    # ── 1막: 경제는 어디에 있나 ──
    MacroSectionMeta(
        "phase",
        "M1",
        "제1막: 경제는 어디에 있나",
        "사이클 4국면 + ISM 재고순환. 지금 어디에 있는가.",
        "현재 경기 국면을 한 문장으로 정의하고, 핵심 근거 3개를 제시하라.",
    ),
    # ── 2막: 왜 여기에 있나 ──
    MacroSectionMeta(
        "causation",
        "M2",
        "제2막: 왜 여기에 있나",
        "기업 이익 방향 + Ponzi비율 + 교역조건. 국면의 미시적 원인.",
        "기업 이익과 교역이 현 국면을 어떻게 만들었는지 인과 체인을 서술하라.",
    ),
    # ── 3막: 정책은 뭘 하고 있나 ──
    MacroSectionMeta(
        "policy",
        "M3",
        "제3막: 정책은 뭘 하고 있나",
        "금리 방향 + 수익률곡선 + 고용/물가 교차. 중앙은행 대응.",
        "물가/고용 상태가 정책을 어떻게 결정하는지 테일러 룰 관점으로 서술하라.",
    ),
    # ── 4막: 금융 시스템은 괜찮나 ──
    MacroSectionMeta(
        "financial",
        "M4",
        "제4막: 금융 시스템은 괜찮나",
        "유동성 + FCI + 신용갭 + HY스프레드 + Minsky + 역사적 맥락.",
        "정책금리가 금융상태를 어떻게 결정하는지, 신용 시스템에 균열이 있는지 진단하라.",
    ),
    # ── 5막: 시장은 어떻게 반응하나 ──
    MacroSectionMeta(
        "market",
        "M5",
        "제5막: 시장은 어떻게 반응하나",
        "5대 자산 신호 + 공포탐욕 + VIX 구간 + Cu/Au.",
        "금융상태가 자산가격과 시장심리에 어떻게 전파되는지 설명하라.",
    ),
    # ── 6막: 앞으로 어떻게 되나 ──
    MacroSectionMeta(
        "outlook",
        "M6",
        "제6막: 앞으로 어떻게 되나",
        "침체확률 + LEI + Sahm + 역사적 유사 시기의 '다음 장' + 시나리오.",
        "현재 상태가 지속될 것인지 전환될 것인지 판단하고, 가장 주의할 시나리오를 제시하라.",
    ),
]
