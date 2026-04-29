# Skills — 독스트링이 SSOT, 별도 skill 파일 없다

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: 검증된 분석·탐색 방법을 코드화하는 철학.
**현재**: 별도 `skills/` 디렉토리 폐지. 모든 skill 역할은 **엔진 docstring** 이 담는다 (2026-04-24 확정).
**방향**: 독스트링 자체 개선 루프로 skill 진화. 개선 과정에서 필요하면 엔진 축도 동반 개선.

---

## 1. 사상 — skill 은 디렉토리가 아니라 독스트링이다

dartlab 은 SSOT 단일 원칙을 지킨다. `skill = 검증된 분석·탐색 방법의 코드화` 라는 개념은 유지하되, **그 코드화의 장소를 별도 파일이 아닌 엔진 docstring** 으로 둔다.

### 왜 별도 skill 파일이 아닌가

- **이중 관리 회피**. `scanRatio` 의 docstring Guide 와 `skills/scan-find-investable/SKILL.md` 는 결국 같은 내용. 파라미터 하나 바꿔도 두 곳 동기화 — 덕지덕지.
- **AI 경로 단일화**. AI 는 tool schema description 을 이미 docstring 에서 자동 수집. skill 카탈로그라는 별도 프롬프트 블록 불필요.
- **사람 경로 단일화**. `help(scanRatio)` · IDE hover · Sphinx 문서 모두 동일 docstring 소비.
- **Simple > Complex**. 새 엔진/축 추가 시 "skill 파일도 써야 하나?" 의 부담 없음.

### skill 개념이 사라지는 건 아니다

- **skill = 검증된 방법의 코드화**. 위치만 다를 뿐 역할은 유지.
- **검증 루프 (audit P → 검증된 레시피 → 독스트링 Guide append)** 는 그대로.
- **자가 개선 (AI 실전 → 반례 발견 → docstring 수정 PR)** 은 그대로.
- **경험축 (When/How/Verified/Examples)** 은 docstring 섹션으로 존재.

---

## 2. 3 층 구조 — docstring 이 담는다

| 층 | 위치 | 담는 것 |
|---|---|---|
| **엔진 사상 · 주요 레시피** | `src/dartlab/{engine}/__init__.py` 모듈 docstring | 엔진 전체 사상, 광역 레시피 (예: scan 4 축 교집합 · 7 관점 · 질문→조합 매핑), 5 단계 워크플로 |
| **공개 함수 매뉴얼** | 공개 함수·메서드 docstring (Google-style 9 섹션) | When (질문 패턴) · How (절차) · Parameters · Returns · Examples · Verified · Notes · Guide · See Also |
| **엔진 간 종합 절차** | `src/dartlab/ai/runtime/` 또는 ai 관련 docstring | 여러 엔진을 엮는 다리 (workflow-diligence 같은 종합 실사) |

AI 가 읽는 경로:
- **tool schema description** = 공개 함수 docstring summary + Returns (기존 `ai/tools/__init__.py::_toolDescription`).
- **Read tool** 로 `src/dartlab/{engine}/__init__.py` 또는 `ops/{engine}.md` 직접 참조 가능.
- 매 요청마다 skill 카탈로그를 시스템 프롬프트에 주입하지 않는다 — tool schema 가 이미 역할 수행.

---

## 3. 자가 개선 루프 — docstring 이 진화한다

5 Phase 를 유지하되 **모두 docstring 위에서** 돈다.

```
A. 실험        AI 자율 실행. audit 로그 축적 ({dataDir}/audit/ai-ask/YYYY-MM-DD.jsonl)
B. 후보 감지   동일 호출 시퀀스가 N 회 P → 독스트링 개선 제안 draft
C. 승격        사용자 confirm 후 docstring PR merge (Guide 섹션 append)
D. 자가 개선   AI 가 반례·엣지케이스 발견 → docstring 수정안 PR
E. 엔진 승격   여러 시나리오에서 반복되는 조합은 공개 함수/축으로 승격 (L2 엔진 axis 신설 · scanRatio 에 ratio 추가)
```

Phase E 가 중요: skill 개선이 엔진 자체를 발전시킨다. 독스트링에서 자주 쓰이는 조합이 보이면 그걸 공식 함수로.

---

## 4. 엔진 축 개선·추가 규칙 (필수)

**축 변경·신설 시 반드시 독스트링을 skill 급으로 유지**. 파라미터 설명만 한 줄 쓰고 끝내지 않는다.

### 기존 공개 함수·축 개선

- SSOT (docstring) 먼저 업데이트. 코드 수정과 동시 커밋.
- 파라미터 이름·시그니처 변경 시 When/How/Examples 섹션의 모든 예시 동반 수정. 호출자도 같이 갱신해 불일치 금지.
- 임계값·해석 규칙 변경은 Verified 섹션에 변경 이력 append (언제 어떤 근거로 변경).

### 새 공개 함수·축 추가

- docstring 9 섹션 모두 채움 필수: Summary · Description · Parameters · Returns · Raises · Examples · Notes · Guide · See Also. `ops/code.md` 참조.
- 단위 (%·원·배·일·점) 반드시 명시.
- When 섹션에 "어떤 질문에 이 축을 쓰나" 트리거 어휘 구체적으로.
- How 섹션에 "다른 축과 어떻게 조합하나" 예시. 단일 축 랭킹만 하지 않도록.
- Verified 섹션은 초기 비어있되 audit P 받으면 append.

이 규칙을 지키지 않는 축 추가는 skill 역할 미실현 → merge 반려.

---

## 5. 검증 인프라 — 여전히 필요

독스트링 SSOT 로 가도 검증 루프는 필요. 2 요소 유지:

### 5-1. audit 로그 축적

`server/streaming.py::stream_ask` 종료 시 `{dataDir}/audit/ai-ask/YYYY-MM-DD.jsonl` 에 구조화 기록. tool_calls · chunk_len · error · 필요시 skill_used (= 호출된 docstring 범위). Phase 1 구현 완료.

### 5-2. 개선 게이트

- audit P 2 회 이상 + 사용자 confirm 1 회 → docstring Guide/Verified 섹션 PR
- 반례 1 건 이상 기록
- 임계값·파라미터 본문 노출 (하드코딩 없음)

게이트는 `scripts/audit/promote_skill.py` (Phase 1 미구현 — 필요 시 추가) 또는 리뷰어 수동 검증.

---

## 6. story · Read · research 관계

- **story** (L3 · 사람용) 는 여전히 블록 템플릿 유지. AI 루트와 분리된 사람 분석 경로.
- **Read tool** 유지. AI 가 `ops/{engine}.md`, `src/dartlab/{engine}/__init__.py`, 코드 심볼을 직접 읽어 상세 참조.
- **blog** 는 `dartlab.io/blog` 웹 경로 → `WebFetch` / 웹검색으로 접근. 로컬 repo 의 blog 디렉토리 직접 접근은 선택.
- **research 방법론** (blog·공시·웹 어떻게 쓰나) 은 `ai/runtime/prompts.py` 시스템 프롬프트 + `ops/ai.md` 에 박힘. 별도 skill 파일 없음.

---

## 7. 관련 문서

- [ops/ai.md](ai.md) — AI 엔진 사상 · tool schema 경로
- [ops/code.md](code.md) — docstring 9 섹션 규격 (SSOT)
- [ops/api-contract.md](api-contract.md) — 공개 함수 추가 규칙
- 프로젝트 최상위 로컬 규칙 — SSOT · Simple > Complex · 덕지덕지 금지 최상위 원칙
- 각 엔진 `__init__.py` 모듈 docstring 과 공개 함수 docstring — skill 역할의 실체

---

## 요약 — 명제 7 줄

1. **skill 은 디렉토리가 아니라 docstring**. 별도 `skills/` 폐지 — SSOT 단일.
2. **엔진 모듈 docstring** 이 사상·레시피, **공개 함수 docstring** 이 세부 매뉴얼, **ai/runtime docstring** 이 다엔진 결합 절차를 담는다.
3. **AI tool 에 skill 카탈로그 주입 없음** — tool schema description (= docstring) 이 이미 그 역할.
4. **축 개선·추가 시 독스트링을 skill 급으로 유지** 의무. When/How/Verified/Examples 모두 채움. 어기면 merge 반려.
5. **검증 루프 5 Phase 는 docstring 위에서 그대로 동작** — audit P → docstring PR → 자가 개선 → 엔진 승격.
6. **Read tool 유지**, blog 는 웹검색, research 방법론은 시스템 프롬프트에 박힘.
7. **엔진 축 개선이 skill 진화의 본체** — docstring 개선이 반복되면 결국 공식 axis 승격으로 이어진다.
