# Ask Workbench Kernel

This file is the AI engine design SSOT while `ops/ai.md` is absent.

> DartLab AI is not a tool-calling chatbot. It is a workbench where a capable LLM reads DartLab, runs DartLab, verifies results, and then answers.

The model must not memorize financial analysis patterns. For every question it
must ground judgment in DartLab's real API, runtime datasets, Python execution
results, and verification refs.

## 1. Core Rule

Simple beats complex.

DartLab must be self-describing:

1. public API docstrings explain how to use DartLab,
2. generated capabilities/reference expose those docstrings in searchable form,
3. shared skills describe reusable analysis procedures without duplicating API schemas,
4. knowledge references describe domain/data/method concepts,
5. runtime datasets reveal schema/latest/entity/metric at execution time,
6. Python execution reveals the real result or the real error.

The AI engine must not add hidden finance case runners or prompt-only knowledge.
Shared skills and knowledge are explicit searchable references consumed by AI, MCP,
story, UI, audit, and external LLM clients.

The kernel must therefore provide a workbench, not a tutor. It gives the model
reference search, runtime dataset inspection, executable Python, and release
verification; it does not teach finance cases through hidden prompts or
question-specific code.

## 2. Non-Negotiable Invariants

1. `dartlab.ask()` and `POST /api/ask` are the only public AI entrypoints.
2. `src/dartlab/ai_backup` is preserved history only. Production AI must not import it.
3. The production AI package is `src/dartlab/ai`.
4. The AI package must not contain an internal `data` module. Runtime datasets are handled by `datasets` and `RuntimeDatasetCatalog`.
5. Shared analysis skills live outside the AI package and are consumed through `dartlab.skills`.
6. The kernel must not contain finance-case runners.
7. The kernel must not contain question-specific Python snippets.
8. The kernel must not contain final-answer templates for market ranking, peer comparison, disclosure analysis, macro analysis, valuation, or any other finance case.
9. The kernel must not classify questions into execution plans.
10. Without an available tool-capable provider, the kernel returns provider-unavailable status and does not pretend to answer.
11. Verification blocks unsupported answer claims: numbers, dates, hidden execution failure, and invalid visuals.

If code violates these invariants, the implementation is wrong even if tests pass.

## 3. System Shape

```text
user
  -> dartlab.ask / POST /api/ask / CLI / web / VSCode / MCP
  -> Ask Workbench Kernel
  -> workbench actions
  -> DartLab libraries + RuntimeDatasetCatalog + Python execution
  -> refs + verification
  -> answer
```

MCP is not the AI engine. MCP is a transport that exposes the same workbench actions to external LLM clients. Internal `/api/ask` must not call MCP stdio; it must share the same Python handlers.

## 4. Workbench Actions

The LLM-facing action surface is small:

```text
search_reference
read_context
inspect_dataset
run_python
finalize_answer
```

Auxiliary action:

```text
compile_visual
```

`compile_visual` is allowed only when it compiles a visual from table/execution evidence. It is not a finance-domain tool.

## 5. Shared Skills and Knowledge

Skills are reusable analysis procedure specs. They are not AI prompts, not API
schemas, and not execution runners.

```text
src/dartlab/skills
  basic      -> generated engine capability maps from public docstrings/capabilities
  capability -> generated API capability views
  domain     -> curated financial analysis procedures under `specs/domain/`
  user       -> project-local `.dartlab/skills/*.yaml`
```

Basic skills are not YAML files and not tool-use tutorials. They are generated
engine capability maps such as `basic.company`, `basic.gather`, `basic.scan`,
`basic.analysis`, `basic.quant`, `basic.macro`, `basic.story`, `basic.credit`,
`basic.industry`, and `basic.viz`. Each basic skill tells the model which
DartLab engine exists, when that engine is generally relevant, and which
capability ids describe the API details. It must not duplicate parameters,
returns, units, or actual output keys.

Workbench action usage lives in action schemas/docstrings:
`search_reference`, `read_context`, `inspect_dataset`, `run_python`,
`finalize_answer`, and auxiliary `compile_visual`. Tool usage is not encoded as
basic skills.

Capabilities answer "what does this API do and return?" and remain sourced from
public docstrings/generated capabilities. Skills answer "what evidence should an
analyst collect for this analysis goal?" and reference capabilities by id. A
SkillSpec must not duplicate API parameters/returns.

Knowledge references are searchable domain/data/method notes. They are not final
answer templates.

SkillSpec may declare `runtimeCompatibility`. This is not API schema
duplication. It only tells a client whether the procedure can run in server,
MCP, or Pyodide/browser environments, which runtime datasets are needed, and
which limitations must be disclosed. Browser execution must prefer HuggingFace
CDN parquet or prefetched files; it must not assume live KRX/DART API access.

DartLab engines are libraries, not LLM-facing tools:

```text
Company
gather
scan
macro
industry
analysis
credit
quant
viz
```

The model uses those libraries inside `run_python`.

## 6. RuntimeDatasetCatalog

`RuntimeDatasetCatalog` discovers datasets from runtime roots:

1. `DARTLAB_DATA_DIR`,
2. local `data/`,
3. installed package or bundled locations,
4. user cache.

It must not use a manual dataset dictionary as SSOT.

Dataset ids are derived from paths:

```text
krx/indices -> krx.indices
krx/prices  -> krx.prices
```

Schema inspection infers:

- date columns,
- entity columns,
- metric candidates,
- latest/asOf,
- row count,
- sample rows.

If latest/asOf cannot be computed, the catalog must say so. It must not invent freshness.

## 7. Refs

All evidence is stored as refs:

```text
docRef
datasetRef
dateRef
executionRef
tableRef
valueRef
visualRef
verifyRef
```

`run_python` emits structured results using the prelude helper:

```python
emit_result(
    rows=[...],
    values={...},
    units={...},
    formulas={...},
    inputs=[...],
    meta={"asOf": "YYYYMMDD"},
    limits=[...],
)
```

The helper writes the stable `DARTLAB_RESULT_JSON=` marker internally. The
kernel may convert that generic execution output into table/date/value refs.
This is not a finance rule.

## 8. Verification

Verification is answer-content based, not question-type based. The verifier must not
read or classify the user question.

Rules:

1. Numeric prose requires matching numeric evidence from table/value refs.
2. Date prose requires date or dataset refs.
3. Execution success claims require a successful execution ref.
4. Failed execution cannot be hidden as success.
5. Visual claims require a visual ref.
6. Visuals require at least two categories and two numeric values.
7. Visuals must be connected to table or execution evidence.
8. Provider prose without `finalize_answer` is not trusted; it is verified as a draft and may be limited.

The verifier must not contain word lists such as "recent", "ranking", or
"analysis" to decide whether execution should have happened. That choice belongs
to the LLM operating the workbench.

## 9. UI, VSCode, MCP

All surfaces consume the same trace/result contract:

```text
reference
inspect
execute
visual
verify
chunk
done
error
```

The UI must not show raw system prompt dumps or large status dumps as transparency. It should show what was searched, inspected, executed, verified, and released.

## 10. Quality Declaration

Implementation complete is not quality complete.

Quality is declared only after direct server/UI/MCP audit shows:

- no calculation avoidance,
- no date confusion,
- no hidden execution failure,
- no unsupported numbers,
- no single-value chart,
- no C/V manual verdict.
