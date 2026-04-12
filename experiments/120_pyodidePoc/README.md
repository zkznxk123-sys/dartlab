# 120 — Pyodide POC

dartlab 을 브라우저(Pyodide/WASM)에서 실행 가능한지 단계별 검증.

## 목표 (Phase 1)

- Pyodide 로드 성공
- polars wheel 설치 성공 (가장 큰 의존성)
- HF parquet CORS fetch 성공
- polars 가 parquet 을 브라우저 FS 에서 로드
- 기본 계정 추출 동작
- JS heap 메모리 < 1GB 유지

## 실행

로컬 HTTP 서버가 필요하다 (CORS + module 로더).

```bash
cd experiments/120_pyodidePoc
python -m http.server 8765
# 브라우저에서 http://localhost:8765/ 열고 [실행] 클릭
```

## 검증 포인트

1. **polars 설치 시간** — 30s 이상이면 UX 허용 불가
2. **HF fetch CORS** — `huggingface.co/datasets/.../resolve/main/...` 에서 CORS 헤더 허용되는지
3. **parquet 로드 크기** — 005930.parquet 이 브라우저에서 몇 MB, 메모리 얼마 먹는지
4. **계정명 컬럼** — DART parquet 의 실제 컬럼명 구조 확인

## 다음 단계

Phase 1 성공 → dartlab wheel 자체 설치 (`micropip.install(url)` 로 HF 에 업로드한 wheel)
→ `Company("005930").analysis("수익성")` 전체 경로 검증

Phase 2 — review 실행
Phase 3 — ask (AI) 연결
