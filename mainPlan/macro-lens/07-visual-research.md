# 07. Visual Research

목적: 매크로 대시보드에서 검증된 시각 문법만 가져오고, DartLab 터미널에 맞지 않는 장식/과잉 차트는 버린다.

## 1. 조사 대상

| Source | Observed pattern | Adopt | Reject |
|---|---|---|---|
| FRED / St. Louis Fed Economy at a Glance | Few key indicators as fast economic snapshot, recession shading, source-backed charts | `LeftRail` floor는 한눈에 보는 스냅샷이어야 한다 | 여러 미니 차트를 좌상단에 쌓는 방식 |
| Atlanta Fed GDPNow | Running model estimate, explicit update date, no subjective adjustment claim | asOf와 모델/데이터 한계 노출 | DartLab을 공식 전망처럼 보이게 하는 문구 |
| NY Fed Weekly Economic Index | High-frequency activity compressed into one timely index with underlying indicator family | driver lineage와 freshness를 함께 보여준다 | 단일 점수로 경제 전체를 판정 |
| OECD Short-Term Indicators / CLI | Country/region indicators, turning-point oriented leading signal | KR/US 비교와 전환 신호 표시 | 전환이 없는데 진행률을 만드는 방식 |
| Eurostat/KOSIS Business Cycle Clock | Four-quadrant cycle location for quick regime recognition | 2x2 ordinal quadrant plane | raw signal 좌표를 연속 산점도로 쓰는 방식 |

## 2. Pattern Decision

### Keep

- At-a-glance macro floor: left rail에서 3초 안에 위치를 읽는다.
- Four-quadrant regime plane: `quadrant.quadrant`를 셀 멤버십으로만 쓴다.
- Update/freshness label: `macro.asOf`와 driver lineage 날짜를 분리한다.
- Evidence-aware rail: observed/prior/template을 선 스타일과 opacity로 분리한다.
- Action bridge: 섹터 chip은 screener filter로 연결된다.

### Reject

- Continuous clock hand, orbit, dial, gauge: 현재 데이터에 history/normalized angle 계약이 없다.
- Sankey/ribbon width: edge magnitude/elasticity가 없다.
- Heatmap wall: 좌상단 floor의 정보 밀도를 망친다.
- One-score regime verdict: `phase`와 `quadrant`가 다른 렌즈라는 사실을 숨긴다.
- Forecast authority wording: GDPNow류 nowcast도 업데이트/모델 한계를 밝힌다. DartLab도 동일하게 정직해야 한다.

## 3. Applied UI Rule

Macro Lens는 다음 순서를 고정한다.

```text
where: RegimeQuadrant
  -> why/path: MacroPathRail
  -> evidence: sourceLineage + evidenceLevel + missing/falsifier
  -> action: sectorFilter/screener
```

시각화가 이 체인 중 하나를 강화하지 않으면 추가하지 않는다.

## 4. Sources

- FRED: https://fred.stlouisfed.org/
- St. Louis Fed Economy at a Glance: https://www.stlouisfed.org/on-the-economy/data/economy-at-a-glance
- Atlanta Fed GDPNow: https://www.atlantafed.org/research-and-data/data/gdpnow
- NY Fed Weekly Economic Index: https://www.newyorkfed.org/research/policy/weekly-economic-index
- OECD Composite Leading Indicator / Short-Term Indicators Dashboard: https://www.oecd.org/en/data/indicators/composite-leading-indicator-cli.html
- Eurostat Business Cycle Clock: https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Business_Cycle_Clock
- KOSIS Business Cycle Clock: https://kosis.kr/visual/bcc/index/index.do?lang=en&page=economyBoard
