# Macro Lens

상태: PRD v1.1 (2026-06-19, expert-reviewed implementation-ready)
출처: `C:\Users\MSI\.claude\plans\graceful-yawning-valley.md`
거처: `ui/packages/surfaces/src/terminal/` + `landing/src/routes/terminal`
목표: 퍼블릭 터미널 좌상단 `마켓 펄스 · 매크로`를 텍스트 카드에서 `경제 위치 -> 전파 경로 -> 섹터/스크리너 행동`으로 이어지는 분석 렌즈로 승격한다.

---

## 문서 지도

1. [01-product-prd.md](01-product-prd.md) — 제품 비전, 사용자 시나리오, 정보 구조, 화면 계약.
2. [02-current-state-audit.md](02-current-state-audit.md) — 현재 코드/데이터 전제 검증과 PRD 교정 근거.
3. [03-expert-debate.md](03-expert-debate.md) — 전문 관점 토론, 기각안, 합성 결정.
4. [04-implementation-plan.md](04-implementation-plan.md) — 단계별 파일 변경, 테스트, 롤백.
5. [05-verification-matrix.md](05-verification-matrix.md) — 수용 기준별 증거와 실행 명령.
6. [06-progress-ledger.md](06-progress-ledger.md) — 진행 기록과 NEXT.
7. [07-visual-research.md](07-visual-research.md) — 매크로 대시보드 시각화 조사와 채택/기각 근거.

---

## 핵심 결정

- 새 라우트, 새 상주 패널, 새 fetch surface는 만들지 않는다.
- 좌상단 기존 `마켓 펄스 · 매크로` 카드와 기존 Macro Lens 다이얼로그 transmission 탭을 제자리 승격한다.
- 강한 기능의 본체는 `macro.json#kr/us/quadrant`, `macro.json#sectorTailwind`, `macro.json#transmission`의 정직한 시각화다.
- 회사 미선택 상태에서도 `MacroGlanceView`는 열린다. 회사 의존 `CompanyMacroLensSnapshot`은 선택 이후 하이라이트/체크리스트에만 붙는다.
- `growthSignal`/`inflationSignal`은 픽셀 좌표로 쓰지 않는다. 비정규 원시값이므로 tooltip/debug 보조값까지만 허용한다.
- `sectorTailwind.blended`가 전부 양수인 현재 v19에서는 하위 섹터를 `역풍`으로 부르지 않는다. 상대 약순풍으로만 표시한다.
- `EDGE_TO_TAILWIND`는 공유 mapper 한 곳만 둔다. `logistics`, `utility`처럼 의미 매핑이 약한 키는 강제로 다른 섹터에 붙이지 않고 `tailwind 미산출`로 렌더한다.
- `['all']` transmission edge는 전 섹터 fan-out으로 펼치지 않고 `전 섹터` pill 1개로 표시한다.
- 전파 경로는 magnitude chart가 아니다. 선 굵기는 고정이고, 증거강도는 opacity/line style로만 표시한다.
- 회사 단위 elasticity, beta, 목표가, 추천, 매수/매도, 위기임박 표현은 금지한다.
- 공개 터미널 UI 변경이므로 commit은 자율, push는 운영자 명시 승인과 스크린샷 눈검수 후에만 한다.
