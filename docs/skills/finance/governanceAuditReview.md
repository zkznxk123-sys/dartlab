---
title: 지배구조와 감사 리스크 점검
skillId: governanceAuditReview
category: finance
---

# 지배구조와 감사 리스크 점검

감사의견, 내부통제, 특수관계자, 지배구조 신호를 공시와 scan 근거로 점검한다.

## Metadata

- id: `governanceAuditReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 지배구조 리스크
- 감사 리스크
- 내부통제와 감사의견
- 분식회계 가능성 점검

## Capability Refs

- `Company.audit`
- `Company.disclosure`
- `Company.readFiling`
- `scan.audit`
- `scan.governance`

## Required Evidence

- target
- period
- table
- basis

## Expected Outputs

- risk thesis
- 공시 근거
- 반대 근거
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 본문 미조회 상태에서는 제목/프리빌드 기준 위험 신호로만 제한한다. |

## Guide

## 절차

- Company.audit, disclosure, scan.audit, scan.governance capability를 확인한다.
- 감사의견, 내부통제, 특수관계자, 지배구조 신호를 기간별 근거로 분리한다.
- 위험 신호와 확정 사실을 구분하고 반대 근거가 있으면 함께 남긴다.
- 본문 조회가 없으면 제목/프리빌드 기준 한계를 명시한다.

## Forbidden

- 분식회계 단정
- 본문 근거 없는 지배구조 비난
