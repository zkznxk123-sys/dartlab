---
title: Pyodide / Web AI 실행 범위
skillId: runtime.pyodideBrowser
category: runtime
---

# Pyodide / Web AI 실행 범위

브라우저에서 가능한 DartLab skill과 제한을 구분한다.

## Metadata

- id: `runtime.pyodideBrowser`
- category: `runtime`
- kind: `curated`
- status: `unverified`
- Pyodide: `supported`

## When To Use

- 파이오디드에서 가능한 분석
- 웹 AI에서 바로 실행 가능한 기능
- HuggingFace prebuilt 데이터 기반 분석

## Required Evidence

- runtimeCompatibility
- dataset

## Expected Outputs

- runtime limits
- available skill list

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `supported` |  |
| `pyodide` | `supported` | live KRX/DART/OpenAI OAuth 호출은 브라우저에서 제한된다. |

## Guide

## 절차

- skill search 결과의 `runtimeCompatibility.pyodide.status`를 먼저 확인한다.
- `supported`는 브라우저 내 파일 또는 prefetch 데이터로 바로 실행할 수 있다.
- `limited`는 HF snapshot, 업로드 파일, prebuilt parquet 같은 제한 조건을 함께 표시한다.
- `unsupported`는 로컬 Python 또는 서버 ask 경로를 안내한다.
- 브라우저에서 말하는 최신성은 live API가 아니라 사용한 snapshot의 asOf 기준으로만 표현한다.

## Forbidden

- Pyodide 가능 여부 허위 단정
