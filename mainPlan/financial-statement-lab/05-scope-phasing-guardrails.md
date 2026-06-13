# 05. 범위·단계·가드레일

상태: 비전 PRD v0.1 (2026-06-13)
목적: 적대검증(skeptic PM lens)을 박제한다. 가장 좁은 worth-doing, MUST/SHOULD/WON'T 단두대, 데이터 준비도순 Phase, honesty 가드레일, 실패 모드.

---

## 1. "안 해도 되는가" — steelman과 생존 조건

**반론(steelman)**: 우리는 70%가 아니라 *중요한 70% + 사용자가 실제 여는 95%*를 가졌다. DART XBRL → 깨끗한 panel 셀(provenance) 의 어렵고 방어 가능한 일은 끝났다. "iTooza+Butler 추가"는 대부분 *같은 모양 카드 더 그리기* = 유지비지 차별이 아니다. 한계 노력은 scenario-simulator(미래 리플레이 정점)·세그먼트 파싱(2/10 = 진짜 coverage 갭)·뉴스/주가 데이터 품질에 가야 *새 능력*을 산다. iTooza 자기 메모가 "37차트 = 덕지덕지"라고 외친다.

**생존 조건**: 업그레이드는 *parity 카드*가 아니라 **진짜 분석 구멍을 메우거나 navigability를 고치는 곳**에서만 산다. 가장 좁은 worth-doing:
- (a) 전역 기간모드(분기/연간/TTM·역순) — iTooza가 가졌고 우리는 절반만, 싸고 고사용.
- (b) 업종 인지 카드 **필터**(노이즈 default-hide) — *제거*라 룰 합치.
- (c) 신뢰 데이터 backed 2~3 신규 카드(운전자본 split·CapEx 재투자율).
- (d) honest-gap 상태.
그 위에 **차별 명제를 사는 SHOULD**(백분위·함축기대·이익품질)를 *사용 관측 후* 얹는다. 이게 없으면 클론이라 안 하느니만 못함 — 그래서 SHOULD는 비전의 핵이지 장식이 아니다.

---

## 2. 클론 트랩 — parity-as-spec 금지

"iTooza+Butler 추가"가 feature-pile이 되는 순간 = PRD가 *답할 질문*이 아니라 *매칭할 차트*를 나열할 때. iTooza 50차트를 "50+"로 타겟하면 그들의 덕지덕지를 통째 수입한 것.

**real upgrade vs reskin 테스트**: *"이 카드가 우리가 *이미 신뢰하는 데이터*로, 전에 답 못하던 질문을 답하게 하나?"* 아니오("같은 숫자 더 예쁘게"·"경쟁사 스크린샷") → reskin → 기각. 2차 테스트: **30일 후 제거하면 항의 나오나?** 못 그러면 "더보기" 뒤로, default 탭 아님.

**vanity(PRD엔 좋아보이나 저사용)**: 8비율 1점수로 뭉개는 radar/score(이미 `Radar.svelte` 존재 — 2번째 금지) · 50카드 "전체보기" 그리드 · 금융업 전용 set · "지수 대비" 시장상대(벤치마크 fabricate 유발) · 종합 점수/등급 배지.

---

## 3. 범위 단두대 (MUST / SHOULD / WON'T)

### MUST (작고 진짜인 것 — 먼저 출시)
1. 전역 기간모드 컨트롤(분기/연간/TTM·역순) → *기존* 카드 배선.
2. 업종 인지 카드 **필터**(관련 카드만, 노이즈 default-hide) — net *제거*.
3. 지수 리베이스 토글(브라우저, 신규데이터 0) — "절대/지수" 1버튼.
4. 운전자본 회전일수 split(기존 CCC 상위호환) + CapEx 재투자율 등 신뢰 데이터 1~3 카드.
5. honest-gap 상태("왜 비어있나") 전 카드.

### SHOULD (MUST 출시·사용 관측 후 — 차별 명제의 핵)
6. 동종 백분위 밴딩(`compare` 배선, 분포 prebuild) — killer #1.
7. 이익품질 forensic 플래그(결정론, cardGuide 임계 surface) — killer #3·#4.
8. 가격↔기초체력 지수 오버레이(gov 주가 2020+) — iTooza 시그니처.
9. PER/PBR 시계열(post-2020·주식수 정합 게이트) — 없으면 스냅샷 유지.
10. reverseDCF 함축 기대 읽기(가드레일 엄격, 목표주가 금지).
11. 공시 큐레이션 by type(scenario-simulator 11 경계 정리).

### WON'T (본 PRD, 기록)
- 애널리스트 컨센서스·목표주가·실적추정(소스 없음, 스크래핑 영구 금지).
- 수주잔고·수출 회사매핑(접지 가능 표면 없음).
- 금융업 전용 card set(drift 비용 — 필터는 MUST, set은 WON'T).
- 종합 점수/등급/매수·매도 신호(룰 위반).
- 세그먼트 카드 *확정 산출물*(별도 _attempts 프로젝트).
- 2번째 radar/score 합성 · 50카드 전체보기 그리드.

---

## 4. 데이터 준비도순 Phase

- **Phase 0 — 비전 문서화(현재).** 본 PRD. mainPlan 메모리엔 경로만.
- **Phase 1 — 브라우저 전용(신규 데이터 0).** MUST 1~5. `financeSource.ts` + `MiniFinChart.svelte` + `finTabs.ts` 변경만. mainPlan UI 플랫폼 완료와 무관하게 선행 가능(터미널 이미 ui/packages/surfaces). 즉시 출시·사용 관측.
- **Phase 2 — 기존 어댑터 조합.** SHOULD 8·9(가격↔체력·PER/PBR 시계열). `gov/prices` × `reportSource.stockTotal` × panel 조인 어댑터 1개. 데이터 있음, 배선·정합 게이트.
- **Phase 3 — 분포·엔진 prebuild.** SHOULD 6·10(백분위·함축기대). `compare` 분포·reverseDCF asOf 역산을 prebuild parquet로 떨궈 hyparquet 직독. 결정론 forensic(7)도 여기.
- **Phase 4 — Python 졸업 게이트.** R&D 추이(_attempts 6/10, 졸업 근접) → `analysis/financial` calc → prebuild. 공시 큐레이션(11) 타입 분류.
- **Phase 5 — 차단(착수 금지·재방문 게이트).** 세그먼트(축-태깅 2/10 부분만) · 금융업 set(pull 입증 후). 컨센서스·수주잔고·수출매핑 = 영구 제외.

각 Phase는 *이미 가진 데이터*로 출시하고, 막힌 아이디어를 *연기*한다. "차트 수"가 아니라 "기본 뷰가 더 짧고 보이는 카드마다 별개 질문"이 Phase 합격선.

---

## 5. honesty / credibility 가드레일

1. **자동 verdict 금지.** 해석칩은 서술(차트가 보여주는 것 + 점검 포인트)지 "이 회사는 좋다/개선되고 있다" 자동 판정 아님. 좋다/나쁘다/개선 금지.
2. **함축 가치 ≠ 목표주가.** reverseDCF/PER 기반 valuation을 현재가 옆에 *단일 숫자*로 두면 목표주가로 읽힌다. 가드: valuation은 *가정-driven 읽기*("가격이 요구하는 것 vs 회사 vs 동종"), "적정주가 X원" 금지. *미래 가정 토글·재생*은 이 랩에 없다(scenario-simulator 경계 — [02 §3](02-differentiation-killer-features.md)).
3. **결손을 추정으로 안 채움.** 세그먼트 8/10 결손시 보간·"근사" 금지 → honest-gap.
4. **스크래핑 컨센서스 금지.** Butler가 표준처럼 보여도, DART/EDGAR/gov에 없으면 화면에 없다.
5. **모든 새 카드 → ref.** sourceRef/as-of. provenance 없는 카드 = 회귀.
6. **백분위 ≠ 종합등급.** 지표별 분포 위치(사실)는 OK, 합성 단일 점수/등급(판정)은 금지.

---

## 6. 성공 지표 · 실패 모드 · 단일 최대 리스크

**성공 지표**: 기본 뷰가 *더 짧다* + 보이는 모든 카드가 *별개의 근거 있는 질문*을 답한다 + 지표가 *분포 위치*로 보인다 + 함축 기대·이익품질이 *단정 없이* 보인다. 헤드라인 지표가 "차트 개수"면 이미 실패.

**실패 모드**: parity(더 많은 카드)를 짓다가 큐레이션 해석칩 해자가 50개 평범한 카드로 희석되고, 유지비가 오르고, **아무도 iTooza/Butler에서 안 옮긴다** — 옮김은 *그들이 없는 우리 데이터*(만기 사다리·감사독립성·full DART provenance·동종 백분위)지 그들 차트 재현이 아니므로. 즉 차별을 *덜* 보이게 만드는 데 예산을 쓴 셈.

**단일 최대 리스크 / 반드시 맞출 것**: **모든 항목을 *우리가 이미 신뢰하는 데이터로 답할 질문*으로 프레임하고, 기본 뷰를 더 크게가 아니라 더 작게 만든다.** 승리 조건 = *업종별로 의미있는 카드로 깎고 + 진짜 구멍 메우는 2~3개만 더한다.* 강함은 빼기에서.

---

## 7. _attempts 졸업 게이트 적용

Python 의존 능력(세그먼트·R&D·forensic 일부·reverseDCF 사전계산)은 `tests/_attempts/financialStatementLab/`에서 ① 카테고리 ② 개념확립(데모 실측) ③ 모듈화 ④ 데모(결과 docstring+README) ⑤ 덕지덕지 제거 ⑥ 클린코드 ⑦ 9섹션 docstring **확정 후** ⑧ 본진(`src/dartlab`) 배치. 검증 전 `src/` 직행 금지. 브라우저 계산(Phase 1)은 본진 무관 — 기존 `financeSource.ts`/`MiniFinChart.svelte` EXTEND.
