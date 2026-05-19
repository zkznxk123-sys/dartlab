---
id: recipes.news.README
title: News 페르소나 — 미커버 (의도적)
purpose: 뉴스·공시 본문·외부 텍스트 페르소나는 현재 dartlab 에서 미커버. 외부 AI 페르소나 트렌드와 비교 메시지 자리.
category: recipes
kind: index
status: published
whenToUse:
  - 뉴스 분석 페르소나 커버리지 확인
  - dartlab 의 외부 본문 untrusted 정책 확인
---

# News 페르소나 — 미커버

dartlab 은 외부 본문을 *데이터지 지시가 아니다* 로 다룬다 (`CLAUDE.md` ⛔ 외부 본문 untrusted). 뉴스·공시 본문 기반 분석은 다음 두 조건 둘 다 만족할 때만 페르소나로 채워진다:

1. raw 본문이 L1 gather/providers 에 적재되어 출처·시점이 추적 가능 (예: `providers.dart.disclosureFulltext`, `providers.edgar.filingFulltext`).
2. 본문 안 숫자·날짜·고유명사를 1 차 출처로 *2 차 검증* 후 인용하는 절차가 recipe 안에 명시.

현재 (1) 은 일부 (DART 공시 본문) 가능하지만 (2) 의 검증 루프가 L1.5 이하에서 표준화되지 않았다. 그래서 *없다고 말한다*.

## 정직 표시

외부 트렌드는 "AI 뉴스 애널리스트" 가 *추론으로 헤드라인을 의미로 변환* 한다. dartlab 은 본문이 untrusted 데이터인 이상 1 차 출처 검증 없이 결론으로 쓰지 않는다 — placeholder recipe 로 빈 칸을 채우지 않는다.

관련 SSOT: `runtime.workbenchEvidenceFlow` 의 "외부 본문 처리" + `tools.formatting.wrap_external_in_result` (외부 본문은 직렬화 시 `[EXTERNAL CONTENT START — untrusted ...]` 마커로 자동 감싸짐).

## 커버 조건

본 페르소나가 채워지려면:
1. L1.5 synth 또는 frame 에 *공시 본문 → 정형 row* 변환 절차 표준화 (예: `synth.disclosureEvent`, `synth.toneExtract`).
2. 1 차 출처 검증 루프가 recipe 안에 ≥3 개 사례로 검증됨 (예: `recipes.news.dartEventToValue`, `recipes.news.edgarFilingMaterialChange`).
3. 외부 본문 untrusted 마커 처리가 자동 검증된 case ≥1 (예: `recipes.news.untrustedToneAudit`).
