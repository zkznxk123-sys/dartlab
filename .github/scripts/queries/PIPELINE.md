# 공시 Q&A 라우팅 — 시드 누적 → HF → 모델 재도출 파이프라인

> 검증된 결정론 메커니즘(intent 라우팅 → 섹션 scoping + canon 어휘보강 → RRF)을 **장기 관리 가능하게** 키우는 설계.
> **held-out(커레이티드에 없는 새 질문) 검증**: 라우팅 **90%**, top-6 섹션도달 **92~94%** (plain BM25 56~71% 대비). 메커니즘=arm E.
> 핵심 규율: ① raw 시드 = HF append-only **무한↑** ② 브라우저 모델 = top-K **bounded**(시드수 무관) ③ raw→curated 승격은 **운영자 게이트**(노이즈 자동유입 0 — round2 casual 노이즈 교훈).

## 파일 (7개) · 단일 명령

| 파일 | 역할 |
|---|---|
| `pipeline.py` | **단일 진입점** — build + verify + 회귀게이트. 시드 추가 후 이거 한 줄이면 끝 |
| `curatedQuestions.json` | 라우팅 학습원 (582 질문, 손 작성 SSOT) |
| `intentSpec.json` | intent → 섹션 target + canon (결정론 SSOT) |
| `heldoutB.json` | 병합 안 한 held-out (일반화 게이트) |
| `intentModel.json` | 빌드 산출물 (~30KB bounded) |
| `uploadIntentModel.py` | HF 업로드 (이관 시) |
| `PIPELINE.md` | 본 문서 |

```
# 시드 추가 = curatedQuestions.json 편집 후 ↓ 한 줄. build·검증·게이트 자동. 신경 끝.
uv run python -X utf8 tests/_attempts/viewerDenseEvidence/pipeline.py
```

## 3 티어 구조

```
Tier 0  curated SSOT (지금 라이브)
  intentSpec.json     24 intent → 실제 섹션 target + canon (결정론)   ← 손 작성, repo 버전관리
  curatedQuestions.json  582 질문 (다양한 레지스터)               ← 손 작성, repo 버전관리
        │ pipeline.py build (route IDF·glue제거·top-K + 섹션 target + canon)
        ▼
  intentModel.json (~30KB, bounded)  ← 번들(dev) / HF(이관 후)

Tier 1  사용자 질문 누적 (append-only, 무한↑)
  HF: dart/queries/raw/YYYY-MM.jsonl   {q, predIntent, score, topSection, clicked?, ts, code}
        │ (수집 메커니즘 — §수집 참조)
        ▼
Tier 2  주기적 재도출 (GitHub Action, offline)
  raw + curated → 큐레이션 게이트 → route 재학습 → intentModel.json 재빌드 → 회귀검증 → HF push
```

## 데이터 흐름

1. **수집** — 사용자가 코파일럿에 질문 → 익명 로그 1줄(질문문·예측intent·점수·도달섹션·근거클릭여부). PII 0.
2. **누적** — `dart/queries/raw/2026-06.jsonl` 에 append. 월 샤드, 영구. 양 제한 없음(샤드는 늘기만).
3. **큐레이션 게이트** (운영자 + 자동보조):
   - 자동: 예측 점수 < 임계 또는 어느 intent 도 0점 = "미라우팅" 버킷으로 분리(새 어휘 후보).
   - 운영자: 미라우팅·신규클러스터를 review → 진짜 의미있는 질문만 `curatedQuestions.json` 에 intent 라벨 달아 승격. **나머지는 route 에 안 들어감**(노이즈 차단 = recipe lifecycle·docstring 안티-auto-sweep 동일 사상).
4. **재도출** — 승격된 curated 로 `pipeline.py` 재실행 → route IDF 재계산·top-K 유지(모델 크기 불변) + 라우팅·top-6 회귀게이트(하락 시 FAIL) 한 번에 → HF push.
5. **소비** — 브라우저가 HF 에서 intentModel.json 1회 fetch(현 dev 는 번들). 시드 100만개여도 모델은 27KB.

## 왜 이 구조인가 (덕지덕지 0)

- **bounded 소비**: route top-K(120/intent) 라 raw 가 무한 늘어도 브라우저 페이로드 고정. dense(30MB)·전체 시드(83KB→∞) 대비.
- **결정론**: 섹션 target 은 실제 DART taxonomy 고정. 학습 0·모델무게 0·매퍼더미 0.
- **노이즈 면역**: round2 casual 자동투입이 라우팅 흔든 교훈 → raw 는 *후보일 뿐*, 운영자 승격분만 route 반영.
- **안전 강등**: 라우팅 틀려도 RRF 가 plain BM25 보존 → 최악도 plain(56~71%), 정상은 92~98%.

## 수집 메커니즘 — 권고 (시뮬레이션 근거)

**시뮬레이션 결과(heldoutB 로 측정)**: 검증된 질문 42개(같은 스타일)를 확정시드로 병합해도 *새 질문(held-out)* 성능 무변(라우팅 82→80%). **볼륨은 포화 — 단순 누적은 일반화 못 키운다.** 반면 *다양한 레지스터/어휘* 117개 추가하니 held-out 라우팅 80→**90%**, 섹션 84→**93%** (실측 개선). ⇒ **수집의 가치 = 양이 아니라 모델이 약한 곳(misroute·low-confidence)의 신규 패턴/어휘.**

권고 = **"불확실 쿼리만 수집 → 자동청소 → 회귀게이트 재도출"** (B 변형, 자동·안정·청결):

1. **무엇을 수집** — 전량 아님. 라우터가 *불확실*한 것만: top-intent 점수 낮음 / no-route / 사용자가 근거 미클릭(암묵 부적합). 고확신 쿼리는 이미 처리됨(수집=낭비, 포화 입증). 페이로드 {q, predIntent, score, clicked}. **opt-in 토글 기본 OFF**(현 "외부 전송 0" 약속과 양립).
2. **수신단** — 정적사이트라 Cloudflare Worker(무료·저유지) 가 HF `dart/queries/raw/YYYY-MM.jsonl` append.
3. **자동청소(더러움 제거, 결정론)** — ① 빈도 게이트: ≥N 세션서 재현된 패턴만(일회성 오타·gibberish 는 재현 안 됨 → 탈락) ② bigram 군집화: singleton=노이즈 탈락 ③ 클릭 일치: 근거 클릭된 군집=라우팅 이미 좋음(불요), 미클릭 군집=라우팅 빵꾸=가치 후보.
4. **승격(레버)** — 신규 어휘(어느 route 에도 없거나 misroute 유발) 보유 군집만 운영자 빠른 review → curatedQuestions.json 추가. *볼륨 아닌 신규성* — 시뮬레이션이 입증한 유일 효과 지점.
5. **재도출 + 회귀게이트(자동·안정)** — GitHub Action 주기 실행: `pipeline.py`(build+verify+gate) → 라우팅/섹션도달 *하락 시 FAIL*(개선-or-동률만 배포). 모델은 나빠질 수 없다 = 안정 보장.
6. **영구 bounded** — route top-K(120) → 시드 무한↑여도 ~28KB.

요약: 효율(불확실 ~10~20%만 수집) · 청결(빈도+군집+클릭 자동탈락 + 신규성 승격게이트) · 안정(회귀게이트는 열화 불가) · 자동(Worker+Action, 운영자는 신규군집 빠른 review 만). **Tier 0(curated)·Tier 2(재도출)는 수집 없이도 지금 동작**(배치 B 84~86% 실측) — 수집은 신규어휘 점진 보강일 뿐.
