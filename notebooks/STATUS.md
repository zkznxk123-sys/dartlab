# Notebooks

**정책 SSOT**: `ops/notebooks.md`
- Colab (`.ipynb`) — 마크다운 설명 셀 조금 + 코드 셀
- Marimo (`.py`) — 코드 셀만 (마리모 UI 에서 마크다운 가독성 낮음 → 쓰지 않는다)
- 두 포맷은 **코드 셀이 1:1 동일**해야 한다.

**Colab 자동 생성**: `uv run python scripts/build/syncColabFromMarimo.py` — 11개 ipynb 를 한 번에 재생성. 마리모를 손으로 고치면 스크립트의 `NOTEBOOKS` 딕셔너리도 함께 고친다.

## Structure

```
notebooks/
├── colab/            # 11 ipynb — 마크다운 + 코드
├── marimo/           # 11 .py   — 코드만 (uv run marimo edit 로 편집)
│   └── samples/      # 내부 검증용 노트북
└── STATUS.md
```

매핑표(각 노트북의 주제) 는 `ops/notebooks.md` 참고.

## Links

- Colab: `https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/{file}`
- Molab: `https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/{file}`
- 로컬 마리모 편집: `uv run marimo edit notebooks/marimo/{file}`
