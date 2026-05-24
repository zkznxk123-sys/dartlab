# dartlab-plugin-example

> dartlab plugin entry-points 진입 *최소* 예시 (T5-2 트랙).
> 본 패키지를 fork 또는 복제해서 새 분석 recipe / tool 을 dartlab 에 등록한다.

## 구조

```
examples/plugin-example/
├── pyproject.toml                          # entry-points "dartlab.plugins" 선언
├── dartlab_plugin_example/
│   ├── __init__.py                         # 패키지 메타
│   └── hello.py                            # PLUGIN_KIND + PLUGIN_SCHEMA + main()
└── README.md                               # 본 파일
```

## 설치 + 확인

```bash
# 개발 중 (editable install)
cd examples/plugin-example/
pip install -e .

# 확인
python -X utf8 -c "from dartlab.core.plugins import discoverPlugins; [print(d.name, d.kind, d.version) for d in discoverPlugins()]"
# → hello unknown 0.1.0

python -X utf8 -c "from dartlab.core.plugins import listPlugins; import json; print(json.dumps(listPlugins(), indent=2))"
# → [{name: hello, kind: example, schema: {inputs: ..., outputs: ..., description: ...}}]
```

## 새 plugin 작성 체크리스트

1. `pyproject.toml` 의 `[project.entry-points."dartlab.plugins"]` 에 등록:
   ```toml
   [project.entry-points."dartlab.plugins"]
   yourPluginName = "your_package.your_module:main_function"
   ```

2. plugin 모듈에 메타 + 함수 선언:
   ```python
   PLUGIN_KIND = "scan" | "analysis" | "tool" | "recipe"
   PLUGIN_SCHEMA = {"inputs": {...}, "outputs": {...}, "description": "..."}

   def main(**kwargs): ...
   ```

3. dartlab 와 같은 환경에 install:
   ```bash
   pip install -e your-plugin-package/
   ```

4. `dartlab.core.plugins.discoverPlugins()` 결과 확인.

## 관련

- [src/dartlab/core/plugins.py](../../src/dartlab/core/plugins.py) — 로더 + introspection (T5-1)
- [src/dartlab/plugins.py](../../src/dartlab/plugins.py) — 실제 PluginContext + discover (기존)
- [TODO.md](../../TODO.md) T5-1 / T5-2 / T5-5 트랙
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — 외부 기여자 PR 흐름
