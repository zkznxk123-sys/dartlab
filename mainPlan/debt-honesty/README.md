# DartLab 부채 감소 (Debt-Honesty)

> 상태: **PRD 확정 (2026-06-21) · 1차(7차원)+2차(미감사 13엔진+landing+ui-packages) 전수조사 = 66 finding · 6 전문가 적대 평가 5라운드(R1~R3 1차 PRD min 97, R4~R5 2차 확장 min 97) → 전원 ≥95 통과(blocking 0) · ground-truth 교정 12+항 반영.** (운영자 goal "dartlab 전수조사 → 약점 개선 플랜 → 개별 95점 냉정평가까지 토론 루프"의 산출물). **커버리지 = 전 엔진+landing+ui-packages(ui/web·blog만 제외).** 착수 = 운영자 go. 백엔드/가드/문서가 주 범위이나 P2 UI 제거는 운영자 push 승인 필수.
> 거처: src/dartlab + tests + .github + ui + 문서. SSOT = `mainPlan/debt-honesty/`.
>
> **구현 상태 (운영자 "정공법으로 끝까지 완성" 지시): MUST(P0+P1) 실질 완료 · 14 commit(미push, 동시 세션 UI interleave로 보류).** P0 9/9 + P1-1·2·3·4·6·7·8B 완료(가드 5종 신규저작/배선·importlib AST 봉합·표면드리프트 정정). P1-5(docstring)=형식주의 함정 확정→부정확 분모 배선 *명시 거부*(좀비 가드 금지). P1-8A(landing)·P2(유령=운영자 결정)·P3(god=위임) 잔여. 구현이 잠재버그 4건·숨은위반 다수·as-built 정정 6항을 추가 표면화. 상세 = [00-eval-ledger.md](00-eval-ledger.md) §5.

---

## 한 줄 결론

**DartLab 전수조사가 드러낸 진짜 부채는 "코드가 더럽다"가 아니라 "보호받고 있다는 믿음과 현실의 간극"이다.** 7개 차원에서 *독립적으로* 같은 병이 나왔다 — 가드가 죽은 경로(`scripts/`·`ops/`)를 가리키고, 강행 가드 다수가 CI에 배선조차 안 됐고(checkAgentBoundary·staleImports·deprecationAudit·untrustedWrapAudit·9섹션 5/6엔진 = **전부 `tests/run.py` 참조 0, 운영자 직접 검증**), 노이즈로 못 켜고(16 false-positive), 광고(MCP "6 종"·"canonical 7")와 실제(advertised 23 도구)가 다르고, 유령 자산(edinet 3,868줄·ui/web 155파일·ui/shared 20파일)이 parity 게이트나 stale 메모리로 박제됐다. **1순위는 새 기능이 아니라 가드망 자체를 실태에 맞추는 것** — 가드망이 실태와 맞아지면 다른 PRD들이 이미 계획한 분해가 비로소 안전해진다.

---

## 조사 방법 (근거)

1. **운영자 직접 정찰** — 레포 지형·부채 원장(44 baseline)·Guard Index·god 파일·stray(전부 gitignored 확인)·PRD 포맷 직접 측정.
2. **7차원 심층 전수조사 워크플로**(`wf_119e02d0-b1d`, 7 finder·245 tool 호출·683K 토큰, effort high, read-only·dartlab import 금지) — 아키텍처/데이터/덕지덕지/테스트/문서/UI/AI 각자 실제 코드를 grep/wc로 측정, 기존 23 mainPlan PRD 교차참조해 *미계획 갭만* 식별.
3. **운영자 ground-truth 직접 검증 7/7 확정** — 가장 하중 큰 주장(죽은 경로·CI 미배선·MCP 드리프트·JSON 중복·ai.persistence·AGENTS.md)을 운영자가 직접 grep으로 확인. census 에이전트 환각 0.
4. **seed 과측 정정** — 에이전트가 운영자 seed를 바로잡음(stale import 73→18, TODO 265→코드3+stub248, noteTaxonomyData/agent.py god 아님). 측정 정의를 PRD에 박제.

---

## 5개 메타-테마 (28 census finding 집약)

| 테마 | 핵심 | phase |
|---|---|---|
| ① **가드 환상** | "기계 강제" 선언 가드 9종이 죽은경로/CI미배선/노이즈로 거짓 | P0·P1 (MUST) |
| ② **유령 자산** | 빌드·import 0인데 parity게이트/stale메모리로 박제된 자산 8종 | P2 (SHOULD) |
| ③ **표면 드리프트** | MCP·AGENTS·catalog·README_EN 광고 ≠ 현실 5종 | P0·P2 |
| ④ **god 무게** | providers 82배·Company god-class·builders.py 6,111줄 등 | P3 (위임·점진) |
| ⑤ **테스트 비율** | viz 6%·macro 6%·story 15% 단위테스트 빈약 | P3 |

**2차 census 보강(§2.8)** — 운영자 "모든 엔진·랜딩·프론트 다 봤나(web·blog 빼고)" 요청에 미감사 13엔진+landing+ui-packages 전수(5 finder). **38 신규 finding**, 같은 5 메타테마 재현 + 새 메커니즘 2종: ① **importlib 문자열 import가 AST 레이어 가드 우회**(analysis→macro L2→L2·synth→frame/scan L1.5 cross — "0건 보장" 거짓) ② **"빌드-후-미배선" 유령 ~6-8K LOC**(analysis/graph 1,147·quant transforms 719·server/api 죽은라우터 1,840·core/plugins 312·ui-pkg throw-stub 7포트 등 — 전부 importer/caller 0). 내 P2-3도 정정(charts.ts 죽음, live=surfaces MiniFinChart 단독). **커버리지 = 전 엔진+landing+ui-packages(ui/web·blog만 제외).**

---

## 문서 지도

1. [00-prd.md](00-prd.md) — **완전 PRD**(plan-deep 자기충족): 한줄결론+비전 · 현상진단(5 메타테마 실측표·file:line·seed정정) · 설계원칙 · Phase P0~P3(28 finding 매핑) · 영향 파일/함수 전수 · 테스트/가드 동행 · 롤백 · 이중평가 · 성공/실패 기준 · census ID→트랙 매핑 부록.
2. [00-eval-ledger.md](00-eval-ledger.md) — 전문가 토론(6 포지션)·적대 평가 점수 이력·ground-truth 교정 기록(95점 달성 과정).

---

## 기존 PRD와의 관계 (중복 0)

본 PRD는 *어떤 기존 PRD도 안 다루는 갭*만 다룬다. `data-build-workbench-ssot`(빌드 흡수)·`frontend-refactor-loop`(ui dedup)·`search-os`·`polars-gpu-backend`·`ai-workbench-connector` 등이 인접하나, **가드망 실태 정정·유령 제거·god-split 트랙 박제는 어느 PRD에도 없는 갭**이다(00-prd §2.7 재계획 금지 목록).
