"""기술적 lens — 가격 추세·거래량·보조지표 중심."""

from .types import Lens

TECHNICAL_LENS = Lens(
    name="technical",
    promptPatch="""관점: 기술적 분석가.
- 가격 추세 (단기·중기·장기) 와 거래량의 일치/괴리를 본다.
- 이동평균·RSI·MACD·볼륨 프로파일 등 보조지표를 보조 근거로 활용.
- 차트 패턴은 사후적으로 보일 수 있음 — 신호 강도와 실패 조건을 함께 명시.
- 펀더멘털 변화와 가격 반응의 시차를 짚는다.
""",
    capabilityHints=[
        "Company.quant",
        "gather.price",
        "quant.factor",
        "Company.show",
    ],
)
