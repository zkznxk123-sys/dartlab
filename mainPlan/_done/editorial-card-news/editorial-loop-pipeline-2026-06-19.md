# 캐러셀 에디토리얼 루프 파이프라인

날짜: 2026-06-19

## 목적

캐러셀은 더 이상 작가 감각이나 "전문가 OK"로 통과하지 않는다. 모든 신규·수정 캐러셀은 `story_brief.json`, `editorial_loop.json`, `editorial_review.md`, 카드, 캡션, 스레드가 같은 질문과 같은 관전 포인트로 닫혀야 한다.

## 필수 루프

1. 기획 3인
   - `News Planner`: 지금 독자가 왜 넘겨야 하는지 결정한다.
   - `Context Planner`: 독자 출발점과 마지막 보상을 연결한다.
   - `Evidence Planner`: 남길 숫자와 버릴 숫자를 정한다.

2. 마케팅 전문가 3인
   - `Product Marketing Lead`: 누가 왜 이 글을 봐야 하는지와 기능·제품 글의 사용 장면을 정한다.
   - `Growth Hook Lead`: 첫 장 훅이 요약이 아니라 피드에서 멈추는 질문인지 본다.
   - `Trust Claims Lead`: 홍보처럼 보이는 문장이 근거와 한계를 같이 갖는지 본다.

3. 작가 3인
   - `Hook Writer`: 첫 장의 질문과 한 문장 메시지를 맞춘다. 첫 장은 정보 요약이 아니라 클릭·저장 판단을 만드는 화면이다. 해당 회사·주제에서 독자가 이미 궁금해하는 압박점을 가장 강한 문장으로 건다.
   - `Structure Writer`: `setup -> turn -> proof -> payoff` 흐름을 맞춘다.
   - `Caption Writer`: 캡션과 스레드가 카드 요약이 아니라 같은 결론으로 닫히게 한다.

4. 평가 5인 1차
   - `Context Editor`
   - `Skeptical Reader`
   - `Caption Editor`
   - `Fact Check`
   - `Visual QA`

5. 아무것도 모르는 독자층 5인 평가
   - `First-time Reader`: 기능명·종목·맥락을 처음 본 사람으로 읽는다.
   - `Non-user Reader`: DartLab 기능이 있는지도 모르는 사람으로 읽는다.
   - `Busy Feed Reader`: 첫 장과 마지막 장만 보고 남는 말이 있는지 본다.
   - `Skeptical Buyer`: 홍보 문구가 과장인지, 실제 쓸 이유가 있는지 본다.
   - `Caption-only Reader`: 캡션만 읽어도 핵심과 마지막 보상이 남는지 본다.

6. 피드백 반영
   - `feedbackActions[]`에 누가 무엇을 고쳤고 결과가 무엇인지 남긴다.

7. 평가 5인 2차
   - 같은 평가 5인과 독자층 5인이 재평가한다.
   - `evaluationRound2[]`는 카드·캡션·스레드·마지막 장이 같은 관전 포인트로 닫혔다는 증거를 남긴다.

## 레인별 파이프라인

레인별 파이프라인은 같은 템플릿이 아니다. `whereToLook[]`도 레인마다 뜻이 다르다.

기술이야기, 기업이야기, 경제이야기, 퀀트이야기는 반드시 별도 파이프라인으로 만든다. 같은 훅 구조, 같은 숫자 카드, 같은 마지막 문장을 재사용하지 않는다. `story_brief.json` 은 현재 레인의 필수 객체 하나만 채운다. 다른 레인의 파이프라인 객체가 함께 있으면 그 캐러셀은 레인 기획이 섞인 것으로 보고 보류한다.

| 레인 | 필수 객체 | 첫 장 | 중간 | 마지막 |
|---|---|---|---|---|
| `기술이야기` | `technologyPipeline` | 기능명이 아니라 사용자의 불편과 사용 장면을 먼저 말한다. | 기능으로 할 수 있는 일, 못 하는 일, 구현 근거를 분리한다. | `무엇을 할 수 있나`, `언제 쓰나`, `어디까지 가능한가`로 닫는다. 투자 관전포인트 금지. |
| `기업이야기` | `companyPipeline` | 그 회사만의 압박 질문으로 시작한다. | 돈이 나는 구조, 숫자가 바뀐 이유, 깨질 조건을 연결한다. | 다음 실적·가격·수주·점유율·마진 중 무엇을 볼지 남긴다. |
| `경제이야기` | `economyPipeline` | 거시 용어가 아니라 내 지갑·회사 비용·산업 흐름에 닿는 질문으로 시작한다. | 큰 흐름이 어떤 경로로 숫자에 닿는지 보여준다. | 확인할 공개 지표와 영향을 받는 주체를 남긴다. |
| `퀀트이야기` | `quantPipeline` | 숫자가 맞아 보이는 순간의 함정을 건다. | 가정, 표본, 비용, 처음 안 쓴 기간, 반례를 풀어쓴다. | 그 숫자를 믿기 전 확인할 조건과 실패 신호를 남긴다. |
| `공시이야기` | `disclosurePipeline` | 공시 제목이 아니라 원문 문구가 바꾸는 일을 묻는다. | 원문 문구, 날짜, 조건, 이해관계자 효과를 연결한다. | 원문에서 확인할 문구·날짜·조건으로 닫는다. |
| `재무이야기` | `financialPipeline` | 계정명이 아니라 돈이 어디에 묶이고 새는지 묻는다. | 계정 위치, 현금 타이밍, 반복/일회성, 사업 흐름을 연결한다. | 다음 재무제표에서 볼 계정·비율·현금흐름으로 닫는다. |

## 파일 계약

모든 통과 캐러셀은 다음 파일을 갖는다.

- `story_brief.json`
- `editorial_loop.json`
- `editorial_review.md`
- `caption.txt`
- `threads.txt`
- `comment_pinned.txt`
- `source_report.md`
- `hook.json`

`story_brief.json` 레인별 추가 필드:

- `technologyPipeline`: `readerStartingPoint`, `featurePlainName`, `userProblem`, `useCase`, `whatUserCanDo`, `proofBoundary`, `closingPromise`
- `companyPipeline`: `companyPressure`, `moneyMechanism`, `numberThatChangesQuestion`, `breakCondition`, `closingIndicators`
- `economyPipeline`: `macroShock`, `transmissionPath`, `whoFeelsIt`, `publicIndicator`, `closingImplication`
- `quantPipeline`: `numberTemptation`, `assumption`, `sampleBoundary`, `costOrFriction`, `failureSignal`
- `disclosurePipeline`: `disclosureTrigger`, `originalWording`, `dateOrCondition`, `economicEffect`, `closingChecks`
- `financialPipeline`: `accountQuestion`, `statementLocation`, `cashTiming`, `recurringVsOneOff`, `closingAccounts`

`editorial_loop.json` 필수 필드:

- `planningRound[]`: 3인 기획 + 마케팅 전문가 3인
- `writerRound[]`: 3인 작가
- `evaluationRound1[]`: 5인 1차 평가 + 마케팅 전문가 3인 + 아무것도 모르는 독자층 5인
- `feedbackActions[]`: 피드백 반영
- `evaluationRound2[]`: 5인 재평가 + 마케팅 전문가 3인 + 아무것도 모르는 독자층 5인
- `finalDecision`: 최종 판정

역할 세트는 정확히 고정한다. `planningRound[]` 는 `News Planner`, `Context Planner`, `Evidence Planner`, `Product Marketing Lead`, `Growth Hook Lead`, `Trust Claims Lead` 를 각각 한 번씩만 담는다. `writerRound[]` 는 `Hook Writer`, `Structure Writer`, `Caption Writer` 를 각각 한 번씩만 담는다. `evaluationRound1[]` 와 `evaluationRound2[]` 는 기본 평가 5인, 마케팅 3인, 무지 독자 5인을 각각 한 번씩만 담는다. 누락, 중복, 임의 역할 추가는 실패다.

## 통과 기준

검사 스크립트:

```bash
python -X utf8 sns/scripts/checkCarouselEditorial.py <post-folder>
python -X utf8 sns/scripts/auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X
```

자동 게이트 통과 조건:

- `story_brief.json` 이 독자 질문, 핵심 답, 왜 봐야 하는지, 마지막 확인 포인트를 갖는다.
- `story_brief.json` 이 레인별 파이프라인 객체를 갖고, 마지막 보상이 해당 레인의 뜻과 맞는다.
- `editorial_loop.json` 이 3기획, 마케팅 3인, 3작가, 5평가, 초보 독자 5인, 피드백, 마케팅 3인 재평가, 초보 독자 5인 재평가를 모두 기록한다.
- `editorial_review.md` 의 각 역할이 `oneLineMessage` 와 `whereToLook[]` 를 근거로 통과 판단을 남긴다.
- `caption.txt`, `threads.txt`, 마지막 카드가 같은 확인 포인트로 닫힌다.
- 첫 번째 장은 `audienceQuestion`, `coreAnswer`, `tension`, `soWhat` 중 최소 두 축을 담는다. `알아봅니다`, `살펴봅니다`, `정리합니다`, `소개합니다`, `기본부터`, `무엇인가요`, `세 가지` 로 시작하는 요약형 커버는 실패다.
- 모든 `editorial` / `editorialBeat` 제목은 정확히 한 구절을 `[[강조]]` 로 감싼다. `accentColor` 만 넣고 `[[ ]]` 가 없으면 강조색은 렌더되지 않으므로 실패다.
- 공개 카드, 캡션, 스레드는 내부 약어와 전문어를 독자 언어로 풀어 쓴다. 예: `OOS`는 `처음에 안 쓴 기간`, `B&H`는 `그냥 들고 갔을 때`, `slippage`는 `원하는 가격에 바로 샀다는 가정`, `Macro Lens`는 `경제 뉴스가 회사 숫자에 닿는 길`로 쓴다.
- 공개 표기는 회사명·주제명·종목코드 6자리로 완성한다. `D01`, `d01`, `E22`, `X03` 같은 내부 발행번호는 폴더명, 제작 메타데이터, QA 기록에서만 관리하며, 카드 이미지, 릴스, 캡션, 스레드, 고정 댓글의 공개 문구에는 들어가지 않는다.
- `기술이야기`는 마지막에 `다음은 뭘 볼까`, `실적`, `주가`, `마진` 같은 투자 관전포인트로 닫지 않는다. 기능 설명·홍보 글의 마지막은 사용 장면, 할 수 있는 일, 한계다.
- 한글이 정상적으로 읽히고, 과도한 물음표나 깨진 인코딩이 없다.
- `reel.json` 이 있으면 캐러셀과 같은 공개언어·강조·브랜드 아바타 규칙을 적용한다.
- "전문 에이전트가 OK했다"가 아니라 카드, 캡션, 리뷰, 렌더 이미지가 같은 결론을 공유한다.

직접 시각 QA 통과 조건:

- 배치 렌더나 연락시트만으로는 통과 처리하지 않는다.
- 단일 포스트를 렌더한 뒤 `01-hook.png` 부터 마지막 카드까지 한 장씩 직접 연다.
- 확인 항목은 강조색, 브랜드, 페이지 점, 제목 줄바꿈, 본문 줄바꿈, 숫자 단위, 마지막 확인 포인트다.
- 실패한 카드는 문구나 자산 경로를 고친 뒤 다시 렌더하고, 수정된 카드를 다시 직접 연다.
- 결과는 `mainPlan/editorial-card-news/direct-visual-qa-2026-06-20.md` 같은 날짜별 직접 QA 문서에 포스트별로 남긴다.

## 100개 챌린지 재개 조건

100개 챌린지는 이 루프를 기본값으로 둔다. 매 사이클마다 5인 평가가 후보를 고르고, 통과 후보만 제작한다. 다음 사이클 진입 전에는 최근 수정 캐러셀 배치 게이트가 녹색이고, 직접 시각 QA 기록이 남아 있어야 한다.
