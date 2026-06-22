# 05. 스코프 · 단계 · 가드레일 · Never-Claim

상태: **v0.3 (2026-06-22)** — R1·R2 정정(Slice 0 분리·회색지대 가드·never-claim 자기적용).

---

## 1. 스코프 경계 (한 문장)
**범위 = 미국 EDGAR를 한국 DART와 *동일 배선*(빌드→라이브러리→계약→소스→서피스→제품)으로 통일하되, US 동등 데이터 없는 항목은 명시하고 비운다. 범위 밖 = US 고유 데이터 엔진 신설(industry/sector/rank)·ui/web·실시간.**

## 2. 슬라이스 묶음 ([정정] 03 상세 요약 — Slice 0/1/2)
**Slice 0 — 선결 데이터(배선 코드와 병렬):**
| 단계 | 핵심 산출 | 완료 게이트 |
|---|---|---|
| S0.1 | panel backfill ([정정] **로컬 resumable rebuild**, cron 제거 f46a58931) | ledger done ≥ S&P500 + 대표 20 native ≠ ∅ |
| S0.2 | edgar/tickers HF publish(DATA_RELEASES 등록) | 퍼블릭 ticker↔CIK range-fetch |

**Slice 1 — 배선 우선(Slice0 위, 코드작업):**
| 단계 | 핵심 산출 | 완료 게이트 |
|---|---|---|
| S1-L2 | resolveMarket(priority-비대칭·{market,cik,ticker}) + 6포트 market + 스위처 | tsc/svelte-check 0 + 단위테스트 |
| S1-L3 | source 분기(+scan duckSql·landing browser·viewer 백엔드 Python) | wiring 감사 위반 0 |
| S1-L4 | 3 surface US 렌더 + EXEMPT 카운트 + **회색지대 4엔진 가드(credit 필수)** | 검증유니버스(S&P500+20) 스크린샷 + svelte-check 0 + 눈검수 |
| S1-L5 | 시장 스위처 출하 | 무회귀 + UI push 승인 |

**Slice 2 — 미빌드 완성(빌드부터 아래로):**
| 단계 | 핵심 산출 | 완료 게이트 |
|---|---|---|
| S2-L0 | scan baking 모델 결정 + docsIndex 재배선 + 가격 baked(라이선스) | 결정된 산출물 baked + backfill 완주 |
| S2-L1 | scan 보조축 dispatch + (별도) 계산정합 census | scan US 보조축 ≠ ∅ |
| S2-L2~L5 | 가격/보조축 배선 | Slice1 배선 재사용 |

## 3. 가드레일 (강행규칙 정합)
- **공동작업대만** (CLAUDE.md): edgar scan 빌드는 `pipeline`/`scan/builders` SSOT 경유. `.github/scripts`에서 엔진 로직 재구현(별도빌드) 금지.
- **공통배선 무변경** (CLAUDE.md UI 데이터): origins registry·fetch core 손대지 않음. source만 market 분기. raw fetch·하드코딩 URL·자체 캐시 Map 신설 0 → `checkUiDataWiring.mjs` 강제.
- **4계층 단방향 import**: L1.5 scan 4형제 cross import 금지 유지. edgar scan builder는 kr builder와 동형이되 cross import 0.
- **비대칭 baseline SSOT**: [확인] `tests/audit/providerSymmetry.py` + baseline 원장 *이미 운영*(P-PR6/7/8 트랙). 신설 아님 — baseline 무증가 + missing 축소. EXEMPT allowlist=코드 상수 `_DART_ONLY`(3-provider).
- **UI push 게이트**: surfaces·landing·ui/apps/local 변경은 운영자 명시 승인("올려"/"발간해") 후에만 push. commit까지만 자율.
- **무회귀**: market 기본값 KR — US 추가가 KR 경로 바이트 불변.

## 4. ★Never-Claim (grep 게이트 — 한계 표기 강제, *자기 PRD까지 적용*)
다음 표현이 코드·UI·문서·**본 PRD 본문**에 0건이어야 한다:
- **"완전 동일"·"100% parity"·"full parity"** (무수식) — EXEMPT 때문에 capability는 동일 아님. "동일 *배선*"으로만.
- **"US 산업 지도"·"US 가치사슬"·"US peer 랭킹"·"US 섹터 분류"** — EXEMPT를 채운 척하는 발명 표면.
- **"세계 최초/유일/기관급"** 무근거 수식.
- **US EXEMPT 패널의 KR 데이터·placeholder 채움** — "데이터 부재"를 숨기는 시각.
- **[신설] 검증 미동반 단정조 — "완성"·"완전 미러"·"비대칭 0"·"전수"·"~95%"**: census/현황 주장은 코드 line 인용([확인]) 또는 게이트 통과 증거 없이 단정조로 쓰지 않는다. v0.1이 이 규칙을 어겨 census가 거짓이었다(01 교훈). [보고]는 [보고]로 표기.

### 4.1 완료 라벨 — EXEMPT 카운트 명시 (자기기만 차단)
"EDGAR 동일 배선 완료"를 단독으로 선언하지 않는다. **항상 "EDGAR 배선 통일 — US 미제공 EXEMPT N항목({industry, sector, sectorParams, rank, network, topicSummaries, report17, …}) 명시"**로, 빈 항목 *수*를 라벨에 박는다. L4는 "가짜 채움 0"(negative)만이 아니라 **"US 화면의 비활성 패널 목록을 명시 카운트로 노출"**(positive 게이트)까지 테스트.

## 5. 비목표 (00 §5 재확인 + 추가)
- US 고유 데이터 엔진 신설(§04 kill 1-3).
- ui/web EDGAR.
- 실시간/장중.
- DART report 17 apiType US 강제(메서드 `report()`는 미러됨).
- EXEMPT 가짜 채움.
- **[신설] EDINET(일본) parity** — [확인] dartlab은 dart/edgar/**edinet** 3-provider. 본 PRD는 US만. 단 비대칭 가드(`providerSymmetry.py`)는 3-provider SSOT이므로 **2-provider로 재설계 금지**(`_EDINET_DEFERRED` 회귀 차단).
- **[신설] analysis/credit/quant/story US 계산정합 구현** — 표면은 미러나 KR 계산가정([확인] `_revenueSelect.py:110`; credit 침묵 KR-garbage). 정합 해소는 S2-L1.2 별도 트랙. **단 Slice 1은 회색지대 가드(S1-L4.3)로 침묵 오염을 선제 차단**(credit None/경고 필수) — 동작 표면 = panel/finance/scan-finance(baked)만 보장.

## 6. 리스크 · 완화
| 리스크 | 완화 |
|---|---|
| US 가격 소스 라이선스/안정성 | L0.2에서 소스 정밀 검토. 불가 시 옵션 C(가격 패널 US 비활성)로 대체. |
| 범위 폭발(EXEMPT 채우기 유혹) | §04 kill-list + never-claim. EXEMPT=비워 두는 배선까지만. |
| KR 회귀 | market 기본 KR + 단위 테스트 + 눈검수 + UI push 게이트. |
| source 분기 drift | resolveMarket 단일 진입점(L2.1) 강제. |
| sharesOutstanding 필드 부재 | XBRL `dei:` 추출 선결 점검(§04 §6). 불가 시 해당 축만 EXEMPT. |
| 패널 평가 미수렴 | 07에 라운드별 score·쟁점 기록. ≥ 합격선까지 반복. |

## 7. 평가 합격선 (패널 반복 종료 조건)
- 각 분야 전문에이전트 평가 점수 전원 ≥ 합의된 임계(예 ≥90/100), confirmed 갭 0.
- 한계 표기(never-claim·EXEMPT 처리) 만장 통과.
- 아래→위 순서·의존이 모순 없음(빌드 전 소스 진입 등 역전 0).
