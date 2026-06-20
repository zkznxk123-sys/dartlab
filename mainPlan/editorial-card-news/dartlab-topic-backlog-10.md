# dartlab 자체 기술/제품 캐러셀 백로그

작성일: 2026-06-19

## 운영 전제

이 문서는 `기술이야기` 레인의 후보 풀이다. 기업 카드와 같은 Hook Engine을 쓰되, 화제성보다 repo 근거와 제품 맥락을 먼저 본다. 제작 직전에는 repo 파일, 테스트, 진행 문서 중 최소 2개 이상으로 현재 상태를 확인한다. 내부 구현어는 후보 메모에만 둘 수 있고, 공개 카드·캡션·스레드에서는 반드시 독자 언어로 번역한다.

강조색은 dartlab 임팩트 컬러 `#fb3f6c`를 기본으로 쓴다. `hook.accentColor`를 명시하지 않은 자체 기술 카드는 실패다.

## 상태값

- `live-check 필요`: 현재 repo 근거 확인 전.
- `ready-brief`: 파일·테스트 근거와 훅이 맞고 이미지 모티프가 잡힘.
- `in-production`: hook.json, caption, source_report 작성 중.
- `rendered`: PNG 렌더 완료.
- `needs-context-gate`: 과거 제작·검수 표기가 있으나 현재 전체 맥락 게이트 통과가 확인되지 않음.
- `passed-visual`: 현재 `checkCarouselEditorial.py` + 전체 배치 감사 + 이미지 직접 검수 완료.

## 후보 10

| # | 상태 | 주제 | 훅 방향 | 실제 사실 축 | 마지막 장 관전 포인트 | 이미지 모티프 | 금지 표현 |
|---:|---|---|---|---|---|---|---|
| 1 | needs-context-gate | 공시검색 sidecar + 터미널 전역 검색 팔레트 | 47만 문서를 다 받지 않고도, 공시를 찾는다 | sidecar 인덱스, range fetch, FilingSearchDialog, hard-negative gate | sidecar 단일화, hard-negative gate, HF flip·운영자 눈검수 | 검은 문서 더미, 노란 검색 빔, postings 조각 | AI 검색 완성, 배포 완료, 전 공시 즉시 정확 |
| 2 | live-check 필요 | 종목코드 하나로 세우는 공시·재무 격자 | PDF 10년치를 표 한 장으로 세운다 | DART 원문, topic-period 정렬, 결손 라벨 | 결손을 0으로 채우지 않는지 | 문서가 노란 격자 표로 접히는 장면 | 모든 회사 완벽 비교, 자동 보정 |
| 3 | needs-context-gate | 정직 백테스트 OS | 수익률보다 먼저 보여줘야 할 것, 거짓말의 위치 | t+1 체결, 비용, 처음에 안 쓴 기간 검증, 경고문 | 신호일·체결일·비용·검증 구간·사라진 표본 | 시간축 차트 위 노란 경고선 | 전략 검증 완료, 미래 수익 |
| 4 | live-check 필요 | AI Workbench Connector | AI가 말하고, DartLab은 증거를 건넨다 | Evidence Pack, external AI handoff, viewer 딥링크 | 답변이 근거 화면으로 돌아오는지 | 외부 AI와 터미널을 잇는 노란 evidence packet | AI가 분석 해결, 추천 |
| 5 | needs-context-gate | 공시 테이블 엑셀 내보내기 | 사업보고서 표, 복붙하지 말고 시트로 꺼낸다 | table extraction, merged cell, sheet naming | 숫자 타입·병합셀·목차별 시트 | 공시 표가 스프레드시트 탭으로 변환 | 모든 표 완벽 추출 |
| 6 | live-check 필요 | Macro Lens | 방향 점수와 근거 신뢰는 다르다 | directionScore, evidenceScore, falsifier, lock state | 반증 조건과 LOCK/OPEN/WATCH | 매크로 보드 위 노란 ref chip | 매크로 예측, 주가 방향 |
| 7 | live-check 필요 | dartlab.compare | 비교는 순위가 아니라 같은 격자에서 시작한다 | 2~6개 회사, topic-period 정렬, honest gap | 결손을 숨기지 않는지 | 여러 회사 표가 한 격자로 정렬 | 랭킹, 추천, 결손 자동 보정 |
| 8 | live-check 필요 | UI Data Workbench | 데이터 호출을 한 줄로 묶어야 화면이 오래 간다 | request(), origin registry, RuntimeCache, dedup | raw fetch 금지와 localApi gate | data origin registry와 cache 레일 | 모든 캐시 문제 해결 |
| 9 | live-check 필요 | Skill OS / evidence-native API guide | 규칙은 말이 아니라 실행 전 로드된다 | start.dartlabSkillOs, operation.* skills, API 가드 | 바꾸기 전 어떤 skill을 읽는지 | skill graph와 guard index | 자동 품질 보장 |
| 10 | live-check 필요 | SNS Evidence Ops | 이미지는 포스트가 아니라 공유자산에서 온다 | sns/assets, sync_assets, source_report, visual check | 공유자산 1벌, source_report, 직접 검수 | asset store와 render pipeline | 이미지 재사용 자동 완성 |
