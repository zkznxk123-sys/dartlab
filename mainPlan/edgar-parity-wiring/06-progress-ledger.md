# 06. Progress Ledger

상태: **v0.3 (2026-06-22)**.

> 실행 진행 + PRD 개선 라운드 기록. NEXT 포인터로 재개.

---

## PRD 개선 라운드 (전문에이전트 평가 수렴 — 상세 07)
| 라운드 | 일자 | 결과 | 반영 |
|---|---|---|---|
| 초안 v0.1 | 2026-06-22 | 3 census 기반 6층 PRD | — |
| R1 | 2026-06-22 | 58/38/58/78/68 (평균≈60). census 다수 거짓 적발 → 작성자 직접 재검증 전건 확인 | **v0.2** 전면 정정 |
| R2 | 2026-06-22 | 88/84/84/89/**91✅** (평균≈87). census 거짓 해소, 2차 정밀화 잔존(credit garbage·tickers publish·backfill 로컬) | **v0.3** 정정(Slice0 신설·회색지대 가드·census 재정정) |
| R3 | 2026-06-22 | L0/L1/L2-L4 = **91/91/91 ✅**(R2 최저 3분야 확인, 코드 전건 정합). PM 89·정직성 91 합격 유지 | **수렴 PASS** — 설계 차단요인 0, 잔존은 구현·실측 |

## 구현 진행 (착수 = 운영자 go) — [정정] Slice 0/1/2
| 슬라이스 | 단계 | 상태 | 비고 |
|---|---|---|---|
| **Slice 0** (선결 데이터, 배선과 병렬) | S0.1 panel backfill | ⬜ | [정정] 로컬 resumable rebuild(cron 제거 f46a58931). ledger done-set 실측 1순위 |
| | S0.2 edgar/tickers HF publish | ⬜ | DATA_RELEASES 등록 — 브라우저 ticker↔CIK |
| **Slice 1** (배선 코드) | S1-L2 resolveMarket+계약 | ⬜ | priority-비대칭·{market,cik,ticker} |
| | S1-L3 소스 분기 | ⬜ | 감사 밖(duckSql·landing·viewer 백엔드 Python) |
| | S1-L4 서피스+EXEMPT+회색지대 가드 | ⬜ | credit 가드 필수·검증 S&P500+20 |
| | S1-L5 스위처 출하 | ⬜ | UI push 승인 |
| **Slice 2** (미빌드 완성) | S2-L0 scan baking·docsIndex·가격 | ⬜ | 라이선스 선결 |
| | S2-L1 보조축 dispatch+계산정합 | ⬜ | 계산정합 별도 트랙 |

## NEXT
1. **운영자 go** → 가장 가치 큰 선결 = **Slice0 S0.1 ledger done-set 실측**(로컬 backfill 완료율 확인) + S0.2 tickers publish 판단.
2. Slice0와 병렬로 **S1-L2(resolveMarket·계약)** 착수(데이터 무관).
3. R3는 v0.3 확정 후 운영자 go 시점 1회(또는 Slice0 실측이 더 가치).

## 미해결 쟁점 (R2 후 정리)
- ✅ US 가격: Slice 분리(Slice1 비활성 C, S2-L0.3 baked A 라이선스).
- ✅ executivePay/relatedPartyTx: 범위 밖(dataWaiting, US=DEF14A/notes).
- ✅ sharesOutstanding: 부분 EXEMPT(US 1값, KR 17-col 불가).
- ✅ sector/GICS: 범위 밖.
- ✅ backfill 형태: 로컬 resumable rebuild(f46a58931) 확정.
- ✅ 식별자 매핑: edgar/tickers HF publish(S0.2) 필요 확정.
- ✅ credit 회색지대: Slice1 가드(S1-L4.3) 필수 확정.
- ⬜ scan baking 모델(KR baked↔EDGAR 라이브) 통일 방식 — S2-L0.1 결정(착수 시).
- ⬜ panel backfill 현 완료율 — S0.1 실측(착수 전).
- ⬜ docsIndex marketNs 비기능 정정 범위 — S2-L0.2.
