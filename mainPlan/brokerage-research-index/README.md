# 증권사 리서치 링크 인덱스 (Brokerage Research Index) — PRD

> **무게중심**: 흩어진 증권사 리서치 리포트를 — 본문은 *생산·호스팅 없이* — 각 증권사 공개 게시판에서 **메타(제목·URL·발간일·증권사·종목)만 자체 스크래핑**해 모아, **날짜순·종목별·검색**으로 호출하는 **합법 링크 인덱스**를 gather 에 짓는다. 본문은 원본 링크아웃.
>
> **한 줄 비전**: 네이버는 리포트를 *모아 보여줄* 뿐 **맞았는지 채점은 안 한다**. dartlab 은 링크 인덱스 위에 1차 데이터(공시·주가·금투협 괴리율)로 **애널·증권사를 채점하는 검증 레이어**를 얹는다 — 우리는 *평가하는 자*.

---

## 한눈 결정 (TL;DR)

- **위치 = 다트랩 공개 gather** (메타=사실 → 공개 OK). 유료/경쟁우위는 P3 채점·별도 제3엔진에서.
- **합법 토대(검증)**: 링크는 한국 확립 판례상 합법(복제·전송 아님). **본문 호스팅만** 라이선스 필요 → 절대 안 함. 목록 통째 스크랩(DB권 회색) ❌ → **각 증권사 공개 게시판 자체 인덱싱**.
- **gather 가 맞다**: 수집=gather SSOT, sync(online)→HF→prebuild(offline) **기존 레일 그대로**. 새 인프라 0.
- **3 호출 = 1 스키마**: `report_id`(url 해시 PK)·`ticker`·`pub_date` 가 날짜순/종목별/검색을 파생.
- **관리 SSOT** = `config.py::BROKERS` dict 한 곳(url+selector+type+enabled).
- **gather 직행 금지** → `tests/_attempts/brokerageIndex/` 졸업게이트부터(5~6개사 + ticker 커버리지 실측).
- **별도 제3엔진(증권사 거래 API·BYO 토큰 자동투자)** 은 이 PRD 아님 — 경계 포인터만.

## 작업 산출 (3문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | 무게중심·비전·문제·**법적 기반**·차별화·NEVER-CLAIM·성공기준 (제품 정본) |
| [01-architecture-and-schema.md](01-architecture-and-schema.md) | **스키마·폴더구조·관리 SSOT·Query API·재사용 지도** (기술 정본) |
| [02-scope-phasing-guardrails.md](02-scope-phasing-guardrails.md) | Phase P0~P3·경계(제3엔진·채점레이어·FnGuide)·가드레일 |

## 출처

본 세션 출처검증(2026-06-24): 대법원 링크 판례(2008다77405·2009다4343, 한국저작권위원회), 네이버 리포트=증권사 맞교환(파이낸셜뉴스 2024-01), 저작권법 제93조 DB권, 금투협 전자공시(dis.kofia.or.kr), FnGuide Data Feed, 각 증권사 리서치 게시판 + KIS/키움/LS OpenAPI(거래 API·리서치 endpoint 부재 확인). dartlab gather→sync→HF 배선 실측 인벤토리.
