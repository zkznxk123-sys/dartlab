"""거시 lens — 금리·환율·경기·정책 환경 중심."""

from .types import Lens

MACRO_LENS = Lens(
    name="macro",
    promptPatch="""관점: 거시 경제 분석가.
- 금리·인플레이션·환율·원자재가 산업·기업에 미치는 경로를 본다.
- 경기 사이클 위치 (확장·둔화·침체·회복) 와 정책 (통화·재정·산업) 의 시차를 고려.
- 글로벌 ↔ 국내 ↔ 섹터 ↔ 기업 4 단 인과를 끊지 않고 짠다.
- 시장 컨센서스와 본인 판단의 차이를 명시.
""",
    capabilityHints=[
        "macro.cycle",
        "macro.rates",
        "macro.fx",
        "macro.commodity",
        "gather.macro",
    ],
)
