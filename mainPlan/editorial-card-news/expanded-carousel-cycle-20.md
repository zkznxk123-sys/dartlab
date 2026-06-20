# 확장 캐러셀 20편 제작 백로그

작성일: 2026-06-19

## 목적

기존 `Company Story`와 `Yellow Lab / Evidence OS` 중심 캐러셀을 6개 레인으로 확장한다.

이 파일의 20편 목록은 기업·경제·공시·퀀트·재무 후보 중심이다. 신규 운영 레인은 6개이며, `기술이야기`는 `dartlab-topic-backlog-10.md`와 D-series 개선 사이클에서 별도 파이프라인으로 운영한다.

1. `기술이야기`
2. `기업이야기`
3. `경제이야기`
4. `공시이야기`
5. `퀀트이야기`
6. `재무이야기`

모든 편은 `story_brief.json -> source_report.md -> hook.json/caption/threads/comment -> checkCarouselEditorial -> editorial_review.md 5역 pass -> render -> visual QA -> checkCarouselEditorial` 순서로 통과해야 한다. 단, 2026-06-20 이후 게이트는 5역만으로는 부족하다. `기획 3인 + 마케팅 3인 -> 작가 3인 -> 평가 5인 + 마케팅 3인 + 아무것도 모르는 독자 5인 -> 피드백 -> 재평가` 루프가 `editorial_loop.json`에 있어야 한다.

## 전문 에이전트 사이클

매 제작 사이클마다 기획 3인, 마케팅 전문가 3인, 작가 3인, 평가 5인, 아무것도 모르는 독자층 5인을 붙인다. 마케팅 3인과 독자층 5인은 1차 평가와 재평가에 모두 들어간다.

| 단계 | 역할 |
|---|---|
| 기획 3인 | News Planner, Context Planner, Evidence Planner |
| 마케팅 3인 | Product Marketing Lead, Growth Hook Lead, Trust Claims Lead |
| 작가 3인 | Hook Writer, Structure Writer, Caption Writer |
| 평가 5인 | Context Editor, Skeptical Reader, Caption Editor, Fact Check, Visual QA |
| 아무것도 모르는 독자층 5인 | First-time Reader, Non-user Reader, Busy Feed Reader, Skeptical Buyer, Caption-only Reader |

| 역할 | 책임 | 차단 질문 |
|---|---|---|
| Context Editor | 카드 제목만 이어 읽어도 질문에서 답으로 가는지 본다 | 그래서 뭐가 남나 |
| Skeptical Reader | 독자 입장에서 훅과 마지막 장의 저장 이유를 본다 | 첫 장만 보고 왜 넘기나 |
| Caption Editor | 캡션이 카드 요약인지, 독자 행동 질문으로 닫히는지 본다 | 캡션만 읽어도 관전 포인트가 남나 |
| Fact Check | 숫자, 사건, 공식 출처, 금지 claim을 본다 | 이 훅의 충격이 사라져도 숫자는 사실인가 |
| Visual QA | 모든 카드의 줄바꿈·단위·시선을 한 장씩 직접 본다 | 화면에서 단어와 단위가 깨지나 |

경제·공시·퀀트·재무 레인은 필요시 전문 역할을 추가한다.

| 레인 | 추가 역할 |
|---|---|
| 기술이야기 | Product Marketing Lead, Growth Hook Lead, Trust Claims Lead |
| 경제이야기 | Macro Editor |
| 공시이야기 | Disclosure Editor |
| 퀀트이야기 | Quant Editor |
| 재무이야기 | Financial Statement Editor |

## 상태값

- `live-check 필요`: 제작 직전 최신 자료 확인 전.
- `ready-brief`: 1차 근거, 훅, 관전 포인트, 이미지 장면 수가 맞아 바로 `story_brief.json` 작성 가능.
- `in-production`: `story_brief.json`, `source_report.md`, `hook.json`, 캡션 작성 중.
- `rendered`: PNG 렌더 완료.
- `needs-context-gate`: 과거 렌더나 리뷰 기록은 있으나 현재 `story_brief` 맥락 필드, 리뷰 grounding, 캡션 게이트를 통과하지 못한 상태. 발행 보류.
- `passed-visual`: 모든 PNG 직접 검수와 현재 editorial gate 통과.

## 공통 금지어

`매수`, `매도`, `더 간다`, `확정`, `보장`, `세계급`, `유일`, `최고`, `완성`, `AI가 해결`, `전 공시 정확`, `미래 수익`, `목표가`.

마지막 장은 항상 `좋다/나쁘다` 가 아니라 레인별 마지막 보상으로 닫는다. `기업이야기`는 다음 숫자와 깨질 조건, `경제이야기`는 공개 지표와 전파 경로, `퀀트이야기`는 조건·표본·비용·반례, `기술이야기`는 사용 장면·가능한 일·한계다.

기술이야기, 기업이야기, 경제이야기, 퀀트이야기는 서로 다른 제작 파이프라인이다. 후보 선정, 첫 장 훅, 숫자 사용, 마지막 보상이 다르므로 한 레인의 문장을 다른 레인에 옮겨 쓰지 않는다. 새 산출물은 현재 레인의 `{lane}Pipeline` 하나만 채우고, 다른 레인의 파이프라인 객체가 함께 있으면 보류한다.

레인별 `story_brief.json` 추가 객체:

| 레인 | 객체 | 필수 필드 |
|---|---|---|
| 기술이야기 | `technologyPipeline` | `readerStartingPoint`, `featurePlainName`, `userProblem`, `useCase`, `whatUserCanDo`, `proofBoundary`, `closingPromise` |
| 기업이야기 | `companyPipeline` | `companyPressure`, `moneyMechanism`, `numberThatChangesQuestion`, `breakCondition`, `closingIndicators` |
| 경제이야기 | `economyPipeline` | `macroShock`, `transmissionPath`, `whoFeelsIt`, `publicIndicator`, `closingImplication` |
| 공시이야기 | `disclosurePipeline` | `disclosureTrigger`, `originalWording`, `dateOrCondition`, `economicEffect`, `closingChecks` |
| 퀀트이야기 | `quantPipeline` | `numberTemptation`, `assumption`, `sampleBoundary`, `costOrFriction`, `failureSignal` |
| 재무이야기 | `financialPipeline` | `accountQuestion`, `statementLocation`, `cashTiming`, `recurringVsOneOff`, `closingAccounts` |

## 20편 백로그

| # | 상태 | 레인 | 주제 | 훅 | audienceQuestion | 사실 축 / live-check | whereToLook | 의미 장면 수 | 이미지 모티프 | 금지 프레이밍 |
|---:|---|---|---|---|---|---|---|---:|---|---|
| 1 | needs-context-gate | 기업이야기 | 삼성바이오로직스 | 바이오 회사인데 신약보다 공장을 본다 | CDMO는 공장 증설이 곧 이익인가? | 삼성바이오로직스 Q1 2026 results, Fact Sheet, Plant 5 램프업, 누적 계약가치 | Plant 5 가동률, 계약가치의 생산·매출·마진 기여, 증설 뒤 영업이익률 | 3 | 바이오리액터, 무균 충전, 품질·공정실 | 계약=이익 확정, 신약 성공주 단정, 독점 |
| 2 | needs-context-gate | 기업이야기 | 삼양식품 | 불닭의 질문은 유행에서 재주문으로 간다 | 불닭 수출은 일회성 유행인가, 반복 판매를 만드는 해외 매대인가? | 삼양식품 회사소개, 연합뉴스 2026.06.05, 불닭 누적 판매량·누적 매출·수출 | 해외 매대 반복성, 증설 이후 실제 가동률·출하, 원재료·환율 뒤 마진 | 3 | 매운 라면 제품, 생산라인, 해외 매대 | 글로벌 1등 확정, 영구 성장, 이익 보장 |
| 3 | needs-context-gate | 기업이야기 | 에이피알 | 화장품 회사가 가전처럼 팔 때 | 뷰티 디바이스는 반복 구매와 채널 경제성을 만들까? | APR 1Q26 Earnings Release, 매출 5,933.56억원, 영업이익률 25.7%, 디바이스 매출 1,327.4억원, 해외 비중 89% | 디바이스 매출 비중, 해외·온라인 채널 믹스, 재구매와 판관비 | 3 | 뷰티 디바이스, 풀필먼트, 해외 매대 | 효능 단정, 반복 구매 보장, K뷰티 수혜 확정 |
| 4 | needs-context-gate | 기업이야기 | 크래프톤 | PUBG는 낡은 게임인가 현금엔진인가 | PUBG는 낡은 게임인가, 아직 크래프톤의 현금엔진인가? | KRAFTON 1Q26 Earnings Release, 매출 1.3714조원, 영업이익 5,616억원, PUBG IP 분기 1조원 초과, 모바일 7,027억원 | PUBG IP 매출 지속성, 모바일·BGMI 트래픽과 결제, 신작·비용 부담 | 3 | 게임 개발 데스크, 라이브 운영센터, 모바일·PC 플레이 화면 | 신작 흥행 확정, IP 수명 영구화, 현금흐름 보장 |
| 5 | needs-context-gate | 경제이야기 | 정책금리와 시장금리 | 정책금리와 시장금리는 다르게 움직인다 | 금리 인하 기대만 보면 왜 틀릴 수 있나? | 한국은행, ECOS, e-나라지표, 채권정보센터, Fed H.15 | 기준금리와 시장금리의 간격, 장단기 금리차, 회사채·대출 스프레드 | 3 | 수익률곡선, 중앙은행 회의실, 시장 금리 보드 | 금리 인하 확정, 역전=침체 확정 |
| 6 | needs-context-gate | 경제이야기 | 원/달러 환율 | 환율은 매출과 비용에 다르게 남는다 | 높은 원/달러 레벨은 모든 수출기업에 좋은가? | FRED DEXKOUS 2026.06.12 1,518.87 KRW/USD, Fed H.10, 기업 환노출 구조 | 해외매출 비중, 원재료·부품 결제 통화, 환손익과 헤지 규모, 마진 변화 | 3 | 환율 보드, 수출 항만, 수입 원가 공장 | 원화 약세=무조건 수혜, 환율 전망 확정, 수출주 추천 |
| 7 | needs-context-gate | 경제이야기 | AI 전력 수요 | AI 서버보다 먼저 필요한 것은 전기다 | AI 투자는 GPU 숫자만 보면 되는가, 전력 수요와 전력망 병목도 봐야 하는가? | IEA Key Questions on Energy and AI, DOE/LBNL 2024 United States Data Center Energy Usage Report | 데이터센터 전력 수요, 계통 접속·변압기 납기, 장비 수주·마진·현금흐름, 효율·건설 지연 변수 | 4 | 데이터센터 전력실, 변압기, 발전 설비, 전력망 관제실 | AI 전력난 영구화, 수혜 확정 |
| 8 | live-check 필요 | 경제이야기 | 해운 사이클 | 해운주는 회사보다 바다가 먼저 움직인다 | HMM은 왜 운임표부터 봐야 하나? | SCFI, 선복량, 유가, HMM DART/IR | 운임, 선복 공급, 유가 | 3 | 컨테이너선, 항만, 운항 관제 | 운임 상승 확정, 사이클 바닥 단정 |
| 9 | needs-context-gate | 공시이야기 | 단일판매공급계약 | 수주는 왜 이익이 아닌가 | 단일판매·공급계약 공시를 보면 바로 실적과 이익을 알 수 있는가? | DART 기업공시서식 작성기준, 금감원 단일판매·공급계약 공시 유의사항, KRX 코스닥시장 공시·상장관리 해설서 | 계약기간·납기, 확정/조건부 계약금액, 매출 인식 시점, 마진 변수 | 3 | 공시 원문, 납기 타임라인, 마진 변수 보드 | 수주=이익, 계약=확정 매출 |
| 10 | needs-context-gate | 공시이야기 | 자사주 취득과 소각 | 자사주 취득과 소각은 완전히 다르다 | 자사주 공시는 모두 주주환원인가? | DART 주요사항보고서, 취득 목적, 소각 여부, 보유 자기주식 | 소각 여부, 취득 목적, 주당 지표 | 3 | 공시 줄, treasury/retired shares 도식, 주당지표 | 주주환원 확정, EPS 개선 보장 |
| 11 | live-check 필요 | 공시이야기 | 정정공시 | 정정공시는 숫자를 고칠 수도, 문구만 고칠 수도 있다 | 정정공시는 무조건 나쁜 신호인가? | DART 정정 전후 공시, rcept_no, 정정 사유 | 정정 사유, 변경 표/본문, 영향 계정 | 3 | 정정 전후 문서, 변경 하이라이트, 타임스탬프 | 정정=분식, 정정=무의미 |
| 12 | live-check 필요 | 공시이야기 | 특수관계자·타법인출자 | 본업 이익처럼 보이는 지분법의 그림자 | 관계회사 숫자는 본업 이익인가? | DART 주석, 관계기업, 지분법손익, 특수관계자 거래 | 지분율, 지분법손익, 거래 금액 | 4 | 주석 표, 지분 네트워크, 손익 브리지, 거래 장부 | 지배 확정, 숨은 가치 단정 |
| 13 | passed-visual | 퀀트이야기 | 백테스트 의심법 | 수익률보다 먼저 보여줘야 할 것 | 백테스트 수익률표는 어디서 독자를 속일 수 있는가? | DartLab BacktestReport/BacktestPreflight, t+1 체결, 비용, 그냥 보유 비교, 처음에 안 쓴 기간 검증, 표본 경고 | 체결·데이터 가정, 비용과 그냥 보유 비교, 표본 경고, 처음에 안 쓴 기간의 변화 | 4 | 신호/체결 타임라인, 비용 드래그, 검증 구간 경계, 생존편향 표본 | 전략 추천, 미래 수익, 수익률 보장 |
| 14 | needs-context-gate | 퀀트이야기 | dartlab.compare | 비교는 순위가 아니라 같은 격자에서 시작한다 | 2개 회사를 비교할 때 먼저 맞춰야 할 것은? | `dartlab.compare`, topic-period 정렬, 2~6개 회사, honest gap | 기간 정렬, 결손 라벨, 비교 대상 수 | 3 | 기간 lock 격자, 빈칸 보존, peer guard | 랭킹, 추천, 결손 자동 보정 |
| 15 | passed-visual | 퀀트이야기 | 매크로 뉴스 | 매크로 뉴스는 점수 하나로 끝나지 않는다 | 금리·환율 뉴스가 뜨면 내 종목에 좋다는 말을 바로 믿어도 되는가? | Macro Lens PRD, redesign PRD, 근거 단계, 회사 손익 경로, 반증 조건 | 뉴스가 건드린 변수, 회사 손익 경로, 근거 단계, 반증 조건 | 4 | 매크로 보드, 전파 지도, 증거 상태 칩, 반증·freshness 레일 | 매수·매도 신호, 매크로 예측, 주가 방향 단정 |
| 16 | live-check 필요 | 퀀트이야기 | 팩터 순위 | 상위 10%가 항상 좋은 뜻은 아니다 | 전종목 스캔은 업종을 섞으면 왜곡되나? | scan/rank, percentile, sector bucket, missing rows | 유니버스, 업종 분포, 결손 행 | 3 | 분포 레일, percentile 격자, 결손 행 | 상위=매수, 순위=품질 |
| 17 | needs-context-gate | 재무이야기 | 영업이익과 현금흐름 | 영업이익과 영업현금흐름이 갈라질 때 | 이익이 나는데 왜 현금이 안 도나? | DART/EDGAR IS·CF, 운전자본, 연결/별도, 분기/누적 | 영업현금흐름, 매출채권과 재고, 연결/별도와 누적 기준 | 4 | 손익계산서, 현금흐름표, 운전자본 브리지, 창고 | 이익=현금, OCF 한 분기만으로 분식 |
| 18 | needs-context-gate | 재무이야기 | CAPEX와 감가상각 | CAPEX는 오늘 돈, 감가상각은 나중 비용 | 투자가 큰 회사는 손익보다 무엇을 같이 봐야 하는가? | IFRS IAS 16, DART 재무제표 현금흐름표·재무상태표·주석 | 유형자산 취득, 감가상각·건설중인자산, 가동률·매출 전환, OCF 대비 CAPEX | 3 | CAPEX 공장 설치, 감가상각 브리지, FCF 검토 | CAPEX=무조건 성장, CAPEX=낭비 |
| 19 | live-check 필요 | 재무이야기 | 연결과 별도 | 연결과 별도는 둘 중 하나가 가짜가 아니다 | 지주회사 숫자는 어느 재무제표로 봐야 하나? | DART CFS/OFS, 주요 종속회사, 내부거래 | 연결 범위, 종속회사, 내부거래 | 3 | 연결 구조도, 별도/연결 표, 종속회사 지도 | 별도만 진짜, 연결만 진짜 |
| 20 | live-check 필요 | 재무이야기 | 매출총이익률과 영업이익률 | 매출총이익률과 영업이익률 사이에서 새는 돈 | 원가가 좋아졌는데 왜 영업이익률은 안 오르나? | DART/EDGAR IS, 원가율, 판관비, R&D·마케팅·손상 | 원가율, 판관비, 일회성 비용 | 3 | 원가 stack, 판관비 브리지, 손익계산서 | 마진 개선 확정, 비용 절감 영구화 |

## 첫 5편 추천 순서

1. `공시이야기 / 자사주 취득과 소각` — evergreen, 독자 효용 높고 공식 공시로 검증 쉬움.
2. `재무이야기 / 영업이익과 현금흐름` — 캡션과 마지막 장의 "그래서 뭐?"가 가장 명확함.
3. `경제이야기 / 정책금리와 시장금리` — 세계경제·국내경제 둘 다 연결 가능.
4. `퀀트이야기 / dartlab.compare` — DartLab 제품성과 퀀트 레인을 자연스럽게 연결.
5. `기업이야기 / 삼성바이오로직스` — 기업 스토리에서 회사 실물·재무·수주가 모두 보임.

## 제작 직전 체크

각 편 착수 전 다음을 먼저 채운다.

```json
{
  "lane": "공시이야기",
  "audienceQuestion": "...",
  "coreAnswer": "...",
  "tension": "...",
  "soWhat": "...",
  "whereToLook": ["...", "...", "..."],
  "{lane}Pipeline": "위 레인별 객체 중 하나만 채운다.",
  "captionThesis": "...",
  "captionClose": "...",
  "forbiddenAngles": ["...", "..."],
  "imageCountDecision": {
    "count": 3,
    "rule": "이미지 수는 고정하지 않고 의미 장면 수로 정한다.",
    "scenes": ["...", "...", "..."]
  }
}
```
