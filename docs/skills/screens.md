---
title: DartLab Skills / Screens
description: scan/gather 기반 후보 발굴, 횡단 비교, 시장 필터링 절차.
---

# Screens

scan/gather 기반 후보 발굴, 횡단 비교, 시장 필터링 절차.

## [전종목 횡단면 주가 스크리닝](screens/crossSectionStockScreen)

런타임 시장 데이터에서 종목 universe와 최신 관측일을 확인한 뒤 조건에 맞는 종목 후보군을 만든다.

- id: `crossSectionStockScreen`
- status: `unverified`
- pyodide: `limited`

## [KRX 지수 강세 분석](screens/krxIndexStrengthReview)

런타임 KRX 지수 데이터에서 최신 관측일과 비교 기간을 확인하고 여러 지수의 상대 강세를 검토한다.

- id: `krxIndexStrengthReview`
- status: `unverified`
- pyodide: `limited`

## [저평가·수익성 종목 후보 찾기](screens/screens-findUndervaluedQualityStocks)

scan과 재무 prebuild를 이용해 밸류에이션이 낮고 수익성 근거가 있는 후보 종목을 횡단면으로 찾는다.

- id: `screens.findUndervaluedQualityStocks`
- status: `unverified`
- pyodide: `limited`
