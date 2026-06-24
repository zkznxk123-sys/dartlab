# 04 · 관점 매트릭스 + 참조HTML 골격 매핑 + C-2 변환표

> 심판 G5(a)·G7 해소: C-2 변환표를 **행 단위로 실제 작성** + conclusion 1줄도 C-2 통과.

## 1. 관점 → 보고서 템플릿 (정적 config, reportTypes.py 정본)

★관점 수 통일(H4): `reportTypes.py` 는 **12 entry**. `thesis`(논제검증)는 hypothesis 입력받아 sections 통째 교체 = 정적 투영 불가 → 제외. 따라서 **정적 투영가능 = 11 관점**(full 포함). `full`(전체 6막·bake 기반 슈퍼셋) = "전체" 탭, `executive` = 기본 탭. 아래 표 = 사용자 노출 11 관점.

각 관점 = `buildReportView` 가 payload 위 투영하는 `{sectionOrder, emphasize, focusQuestions, detail}`. **신규 관점 발명 0** — reportTypes.py 그대로.

| 관점 | 독자 | sectionOrder(요지) | focusQuestions 예 | detail |
|---|---|---|---|---|
| **full** | 기본/전체 | 6막 전 섹션(catalog 순서) | (관점 미지정 시 바텀업 인과 서사) | full |
| **executive** | 의사결정자 | 종합평가·수익구조·현금흐름·가치평가 | "한 문장 결론은?" "돈 버는 구조인가?" | 간결 |
| **credit** | 여신/채권 심사역 | 안정성·현금흐름·자금조달·효율성·신용평가 | "부채 감당 현금흐름 있나?" "차환 리스크는?" | full |
| **valuation** | 가치투자자 | 가치평가·수익성·성장성·매출전망·자본배분 | "적정 가치는?" "안전마진 있나?" | full |
| **growth** | 성장투자자 | 수익구조·성장성·매출전망·투자효율 | "성장 원천은?" "ROIC 로 돌아오나?" | full |
| **crisis** | 위험 진단 | 매크로·안정성·자금조달·현금흐름·이익품질 | "단기 현금 마를 위험?" "이익 진짜인가?" | full |
| **audit** | 감사/포렌식 | 이익품질·재무정합성·안정성·지배구조·공시변화 | "이익 현금전환 정상?" "공시 달라진 것?" | full |
| **dividend** | 인컴 투자자 | 수익구조·현금흐름·자본배분·자금조달 | "배당 FCF 커버?" "총환원율은?" | full |
| **governance** | 거버넌스 | 지배구조·자본배분·공시변화·종합평가 | "임원보수 실적과 맞나?" "지분 구조는?" | full |
| **macro** | 탑다운 | 매크로·시장분석·매출전망·가치평가 | "사이클 어디?" "매크로 민감도?" | full |
| **dashboard** | 스냅샷 | 종합평가·수익구조·수익성·현금흐름·안정성·자본배분·가치평가 | 8질문 패턴 | 간결 |
| ~~thesis~~ | — | **제외** — hypothesis 입력받아 sections 통째 교체([`registry.py:1574`](../../src/dartlab/story/registry.py#L1574) 근방) = 정적 투영 불가 | ask 워크벤치 전용 | — |

★실제 **활성 표시되는 관점**은 `payload.meta.publishablePerspectives`(P0 spike 실측). 미충족 관점은 탭에서 dim + "이 회사는 [관점] 발행 기준 미달" 표기. **"11개 다 발행" 인상 금지**(NEVER-CLAIM).

## 2. 참조HTML 골격 → story 섹션/블록 매핑

참조(그랜터커머스 월간 경영성과 보고서)의 문서 골격을 dartlab 자산에 1:1 매핑. **구현 확인된 것 / 매핑되는 것 / 생략**을 구분.

| 참조HTML 섹션 | dartlab 매핑 | 상태 |
|---|---|---|
| 경영 요약(한 줄 요약) | `summaryCard.conclusion`(narrate, ★C-2 통과 §4) + focusQuestions 칩 | 구현됨 |
| 손익 현황 | 수익구조(segmentComposition) + 수익성(marginTrend·dupont) | 구현됨 |
| **손익분기·안전마진**("본전까지 여유") | 비용구조 `breakevenEstimate`·`operatingLeverage`([`builders.py:1784,1805`](../../src/dartlab/story/builders.py#L1784)·registry 586/596/604) | **구현 확인됨** — 참조HTML DNA 핵심 강점, spike 는 coverage 만 측정(과보수 금지) |
| 재무상태 | 안정성(`leverageTrend`·`distressScore` Altman Z) + 자금조달(liquidity) | 구현됨 |
| 자금·현금흐름("운영 가용일수"·위험선) | 현금흐름(`cashFlowOverview`·`cashQuality`) + 자금조달(cashFlowStructure) | 구현됨 |
| 월 비용 구조(고정/변동) | 비용구조 `costBreakdown` | 구현됨. ★costBreakdown SSOT **확정**(H6): 비율 블록(매출원가율·판관비율·DOL) = story/analysis 소유, 보고서가 렌더. periodic-dossier 의 *비용 성격별 raw 명세*(주석 행)는 dossier 소유 → 보고서는 **링크만**(동일 숫자 이중경로 금지) |
| 세무 일정 | — | **생략**(상장사 분기보고서엔 무의미) |
| 리스크 | threads(severity) + flags + valuationSins | 구현됨 |
| 예측 | 매출전망 `revenueForecast` + `calcPlausibilityBand` 동반("추정" 명시), 궤적/what-if = scenario-sim 링크 | 구현됨(닻 필수) |
| 6막 헤더 | `getSectionMeta(key).act`→ACT_HEADERS (F1 재정정: catalog 기존 필드·manifest 이미 baked, `partId.split` 폐기) | 기존 필드 |

**평이언어 리본.** 참조HTML 의 "위험선 근접"·"본전까지 여유" 같은 평이언어는 **본문화하지 않는다** — narrate 프로즈는 conclusion 1줄 + severity 색분류에만 한정하고, 보고서 본문은 raw 블록(표/지표) 우선. 평이언어 단정형용사는 아래 C-2 변환표로 측정값 치환.

## 3. 회계사 단정 → 증거 프레임 3튜플

참조HTML 은 회계사 서명 하에 "양호/주의/조치 필요" 단정을 한다. dartlab 공개 보고서는 **주체중립 + 판정 환산 금지**. 모든 단정을 **3튜플 {측정값, 분위, 출처}** 로 변환:

- **측정값** = builders 실수치.
- **분위** = **자기이력분위**(story-local 가능)만 1차. ★**유니버스분위는 fin-stmt-lab(L2) 소유** → story(L3)에서 호출 시 import 방향 위반 → 유니버스분위는 fin-stmt-lab 링크로 핸드오프(자체 계산 금지, 07 경계).
- **출처** = 블록 `sourceEngine` 라벨 + evidenceIds 칩.

## 4. ★C-2 변환표 (행 단위 — 정본 박제)

참조HTML(및 narrate)의 **판정형용사**를 **측정값 + 자기이력분위 + sourceEngine** 으로 1:1 치환하는 변환표. 보고서 본문·conclusion 1줄 **모두** 이 표를 통과(G7 — conclusion 도 raw 판정어휘 금지).

| 판정형용사/평이언어 (금지) | → 변환 (측정값 + 자기이력분위 + 출처) | 블록 근거 |
|---|---|---|
| "수익성 — 양호" | "영업이익률 13.0% · 자기 8분기 상위 25% · `sourceEngine:analysis`" | marginTrend |
| "자금 — 주의" / "운영자금 빠듯" | "유동비율 110% · 자기이력 하위 30% · 이자보상배율 4.2x · `credit`" | liquidity·coverageTrend |
| "위험선 근접" | "Altman Z 1.9(grey zone 1.8–3.0) · 자기 4분기 하락추세 · `credit`" | distressScore |
| "본전까지 여유" / "안전마진" | "손익분기 달성률 121% · 안전마진 17% · `analysis`" | breakevenEstimate |
| "현금 충분" | "영업CF/순이익 108% · 자기이력 상위 40% · FCF +X억 · `panel`" | cashQuality·cashFlowOverview |
| "채권 — 조치 필요" | "매출채권회전일 62일 · 자기 8분기 +14일 악화 · `analysis`" | workingCapital·cccTrend |
| "성장 견조" | "매출 YoY +18.2% · 3y CAGR 11% · 자기이력 상위 20% · `analysis`" | growthTrend·cagrComparison |
| "이익 양호/진짜" | "발생액비율 −2%(낮을수록 양호) · Beneish M −2.5 · `analysis`" | accrualAnalysis·beneishMScore |
| "저평가/고평가" | "PER 9.2x(인라인·panel) · 동종 백분위·DCF 안전마진 → fin-stmt-lab/JUDGE 링크, **미착수 시 '가치평가 닻 보류' honest-skip**(죽은 링크 금지)" | valuationSynthesis(현재값 인라인·분위 링크) |

**규칙.** 표에 없는 판정형용사가 출력되면 **claimGuard(06)가 발행 거부**. conclusion 1줄 = "영업이익률 13.0%로 자기이력 상위 25%이나 Altman Z 1.9로 안정성 하락추세" 식 — 측정값 합성, "양호/주의" 어휘 0.

## 5. 관점 lock (블렌딩 금지)

1보고서 = 1관점. `emphasize` ★만 강조, **타관점 섹션 import 금지**, 헤더에 관점명 명시. credit 보고서에 valuation DCF 를 끌어오지 않음(필요 시 valuation 관점 탭 전환 또는 fin-stmt-lab 링크).
