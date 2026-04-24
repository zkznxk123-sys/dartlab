# 이슈 관리

**주체**: GitHub Issues + CHANGELOG.md + TODO 코멘트 (3 채널 역할 분담).
**현재**: 별도 이슈 폴더 없음 · 기존 인프라 3 개가 역할 분담 · 수정 → 테스트 → 커밋 추적.
**방향**: P0 · P1 등급 라벨링 표준화 · 릴리즈 노트 자동 집계.

GitHub Issue → 수정 → 테스트 → 커밋 의 추적 체계. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 별도 이슈 폴더 없이 기존 인프라 3 개로 분담한다

| 역할 | 어디에 | 예시 |
|---|---|---|
| 원인 분석 + 논의 | **GitHub Issue** | `gh issue view 15` |
| 재발 방지 | **기능별 테스트 파일** | `test_select.py` 안에 regression 케이스 |
| 코드 변경 이유 | **커밋 메시지** | `fix: select 세전이익 매핑 오류 (#15)` |

**반복 실패** — `tests/issues/` 폴더 생성 → 파일 무한 증식. 이슈별 마크다운 문서 생성 → GitHub Issue 가 이미 추적하는데 중복.

---

## 2. 연결 구조 — 테스트 docstring → 커밋 메시지 → Issue 로 역추적한다

```
테스트 docstring: """Regression for #15."""
        │
        ▼
커밋 메시지: fix: ... (#15)
        │
        ▼
GitHub Issue #15: 근본 원인, 재현 코드, 논의 전부
```

**역추적 경로**: 테스트 깨짐 → docstring 에서 `#15` 발견 → Issue 에서 원인 확인 → `git log --grep="#15"` 로 수정 코드 확인.

**반복 실패** — 이슈 번호 없는 regression 테스트. 나중에 왜 있는지 모른다.

---

## 3. 이슈 수정 — 6 단계로 진행한다

1. **재현** — 로컬에서 버그 재현 (수동 실행).
2. **원인 분석** — 코드 추적, 근본 원인 파악.
3. **테스트 작성** — 기능별 테스트 파일에 regression 케이스 추가.
   - docstring 에 `Regression for #N` 표기.
   - 수정 전 FAIL 확인.
4. **수정** — 코드 수정.
   - 수정 후 PASS 확인.
5. **커밋** — `fix: 설명 (#N)` 형식.
   - GitHub 이 자동으로 Issue 에 커밋 링크 연결.
6. **Issue 답변** — 원인 + 해결 요약, `Fixes #N` 으로 자동 닫기.

---

## 4. 테스트는 기능별 파일에 통합한다

```
tests/
├── test_select.py       ← select 관련 이슈 (#14, #15)
├── test_company.py      ← Company 관련 이슈
├── test_analysis.py     ← analysis 관련 이슈
└── ...
```

이슈별 파일을 만들지 않는다.

---

## 요약 — 명제 4 줄

1. 이슈는 GitHub Issue · 테스트 · 커밋 메시지 3 채널에 역할 분담, 별도 폴더·문서 없음.
2. 테스트 docstring `Regression for #N` → 커밋 `fix: ... (#N)` → Issue #N 역추적 경로를 유지한다.
3. 수정은 재현 → 원인 → 테스트 (FAIL) → 수정 (PASS) → 커밋 → `Fixes #N` 6 단계.
4. 테스트는 `test_select.py` 같은 기능별 파일에 통합, 이슈별 파일 만들지 않는다.
