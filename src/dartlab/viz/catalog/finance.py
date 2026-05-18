"""재무제표 dashboard 카드 카탈로그 — SSOT.

각 entry 는 모양 (kind/seriesPlan/options) + 기본 색상 + 데이터 정의까지
한 곳에 박는다. builder 는 norm DataFrame 만 받아 catalog 의 SeriesPlan 보고
자동으로 추출/합성/비율/YoY 계산. statements 함수 신설 0.

SeriesPlan 데이터 정의 우선순위 (한 series 마다 하나):
  - ratio   : {num: {accountKey: sign}, den: {accountKey: sign}, scale?: int}
  - yoy     : "accountKey"
  - compose : {accountKey: sign}
  - account : "accountKey"

accountKey 는 `accounts.STANDARD` 28 항목 중 하나:
  revenue, costOfSales, grossProfit, operatingIncome, netIncome,
  sga, rnd, financeIncome, financeCosts, incomeTax,
  assets, currentAssets, nonCurrentAssets, cash, inventories, receivables,
  liabilities, currentLiabilities, nonCurrentLiabilities, payables,
  shortDebt, longDebt, equity, retainedEarnings,
  cfOperating, cfInvesting, cfFinancing, capex, dividendsPaid.
"""

from __future__ import annotations

from dartlab.viz.palette import COLORS
from dartlab.viz.schema import CatalogEntry

FINANCE_CARDS: dict[str, CatalogEntry] = {
    # ─────────────────────────────────────────────────────────────
    # 0. KPI strip — overview 최상단 핵심 지표 4 (매출·영업이익·ROE·부채비율).
    # ─────────────────────────────────────────────────────────────
    # 4 개 KPI 를 각각 분리된 카드로 — bento grid 첫 row 4 칸을 채운다.
    "kpiRevenue": {
        "kind": "kpiTile",
        "title": "매출",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "growth",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {"label": "매출", "account": "revenue", "unit": "원", "intent": "primary"},
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "최근 매출 + 전기 대비. 본업 규모 변화 첫 신호.",
    },
    "kpiOperatingIncome": {
        "kind": "kpiTile",
        "title": "영업이익",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {"label": "영업이익", "account": "operatingIncome", "unit": "원", "intent": "positive"},
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "본업 수익성. 매출 대비 비율은 영업이익률 카드 참조.",
    },
    "kpiRoe": {
        "kind": "kpiTile",
        "title": "ROE",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {
                    "label": "ROE",
                    "ratio": {"num": {"netIncome": 1}, "den": {"equity": 1}, "scale": 100},
                    "unit": "%",
                    "intent": "primary",
                },
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "자기자본수익률. 주주 자본 대비 이익 창출 능력. 15%+ 우량.",
    },
    "kpiDebtRatio": {
        "kind": "kpiTile",
        "title": "부채비율",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {
                    "label": "부채비율",
                    "ratio": {"num": {"liabilities": 1}, "den": {"equity": 1}, "scale": 100},
                    "unit": "%",
                    "intent": "negative",
                },
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "부채/자본. 200% 이상은 재무 부담. 50% 이하는 보수적 자본구조.",
    },
    # ─────────────────────────────────────────────────────────────
    # 1-A. 자산구조 — dual-stack (자산 막대 ‖ 부채+자본 막대).
    #      회계 등식 자산 = 부채 + 자본 → 두 막대 동일 높이로 시각 확인.
    #      매출채권·재고도 영업자산 분류에 속하므로 stack 안에서 별도 색.
    #      "기타 영업자산" = assets − cash − receivables − inventories
    #      (= 비유동 영업자산: PPE · 무형 · 관계사 등).
    # ─────────────────────────────────────────────────────────────
    "assetComposition": {
        "kind": "trend",
        "title": "자산구조",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            # ── 자산 stack ─────────────────────────────────────
            {
                "key": "cash",
                "label": "현금성자산",
                "color": COLORS[5],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "asset",
                "account": "cash",
            },
            {
                "key": "receivables",
                "label": "매출채권",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "asset",
                "account": "receivables",
            },
            {
                "key": "inventories",
                "label": "재고자산",
                "color": COLORS[6],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "asset",
                "account": "inventories",
            },
            {
                "key": "opAssetCore",
                "label": "기타 영업자산",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "원",
                "type": "bar",
                "stack": "asset",
                "compose": {"assets": 1, "cash": -1, "receivables": -1, "inventories": -1},
            },
            # ── 부채+자본 stack ────────────────────────────────
            {
                "key": "opLiab",
                "label": "영업부채",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "liabEq",
                "compose": {"liabilities": 1, "shortDebt": -1, "longDebt": -1},
            },
            {
                "key": "finDebt",
                "label": "금융부채",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "liabEq",
                "compose": {"shortDebt": 1, "longDebt": 1},
            },
            {
                "key": "capitalStock",
                "label": "자본금",
                "color": COLORS[4],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "liabEq",
                "account": "capitalStock",
            },
            {
                "key": "retainedEarnings",
                "label": "이익잉여금",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "원",
                "type": "bar",
                "stack": "liabEq",
                "account": "retainedEarnings",
            },
            {
                "key": "otherEquity",
                "label": "기타자본",
                "color": COLORS[7],
                "intent": "primary",
                "unit": "원",
                "type": "bar",
                "stack": "liabEq",
                "compose": {"equity": 1, "capitalStock": -1, "retainedEarnings": -1},
            },
        ],
        "options": {"stacked": True, "unit": "원", "dualStack": True},
        # layout 4×4 는 resolveLayout 의 trend 자동 보정 (시리즈 9 ≥ 6) 과 동일 — 명시 생략.
        "help": "자산(왼쪽) = 부채+자본(오른쪽). 두 막대 높이는 항상 같다 (회계 등식). 매출채권·재고도 영업자산이지만 운전자본 회수기간 신호로 따로 분리. 기타 영업자산은 PPE·무형·관계사 등 비유동 본업 자본. 금융부채 ↑ 이자 부담, 이익잉여금 ↑ 내부유보 건전.",
    },
    # ─────────────────────────────────────────────────────────────
    # 1-B. 부채 상세 (매입채무 → 기타 영업부채 → 단기차입금 → 장기차입금·사채)
    # ─────────────────────────────────────────────────────────────
    "liabilityDetail": {
        "kind": "trend",
        "title": "부채 상세",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "payables",
                "label": "매입채무",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "liab",
                "account": "payables",
            },
            {
                "key": "otherOpLiab",
                "label": "기타 영업부채",
                "color": COLORS[6],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "liab",
                "compose": {"liabilities": 1, "payables": -1, "shortDebt": -1, "longDebt": -1},
            },
            {
                "key": "shortDebt",
                "label": "단기차입금",
                "color": COLORS[7],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "liab",
                "account": "shortDebt",
            },
            {
                "key": "longDebt",
                "label": "장기차입금·사채",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "liab",
                "account": "longDebt",
            },
        ],
        "options": {"stacked": True, "unit": "원"},
        "layout": {"colSpan": 1, "rowSpan": 3},
        "help": "매입채무는 무이자 영업부채 (좋은 부채). 단기차입금 ↑ 은 자금 압박 신호. 장기차입금·사채는 만기 분산되지만 이자 비용 부담. 영업부채 비중이 크면 운전자본으로 자금 조달 — 건전.",
    },
    # ─────────────────────────────────────────────────────────────
    # 1-C. 자본 상세 (자본금 → 자본잉여금 → 이익잉여금 → 기타자본)
    # ─────────────────────────────────────────────────────────────
    "equityDetail": {
        "kind": "trend",
        "title": "자본 상세",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "capitalStock",
                "label": "자본금",
                "color": COLORS[5],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "eq",
                "account": "capitalStock",
            },
            {
                "key": "capitalSurplus",
                "label": "자본잉여금",
                "color": COLORS[4],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "eq",
                "account": "capitalSurplus",
            },
            {
                "key": "retainedEarnings",
                "label": "이익잉여금",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "원",
                "type": "bar",
                "stack": "eq",
                "account": "retainedEarnings",
            },
            {
                "key": "otherEquity",
                "label": "기타자본",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "원",
                "type": "bar",
                "stack": "eq",
                "compose": {"equity": 1, "capitalStock": -1, "capitalSurplus": -1, "retainedEarnings": -1},
            },
        ],
        "options": {"stacked": True, "unit": "원"},
        "layout": {"colSpan": 1, "rowSpan": 3},
        "help": "이익잉여금이 매년 누적 증가하면 건전한 내부유보. 자본금 변동 없이 잉여금만 증가하면 이상적. 기타자본 음수는 자기주식 매입 (주주환원). 자본잉여금은 주식발행초과금.",
    },
    # ─────────────────────────────────────────────────────────────
    # 3. 손익구조 (매출 bar + 영업이익·당기순이익 area)
    # ─────────────────────────────────────────────────────────────
    "incomeBreakdown": {
        "kind": "trend",
        "title": "손익구조",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "revenue",
                "label": "매출액",
                "color": COLORS[2],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "account": "revenue",
            },
            {
                "key": "operatingIncome",
                "label": "영업이익",
                "color": COLORS[3],
                "intent": "accent",
                "unit": "원",
                "type": "line",
                "axis": "right",
                "account": "operatingIncome",
            },
            {
                "key": "netIncome",
                "label": "당기순이익",
                "color": COLORS[1],
                "intent": "primary",
                "unit": "원",
                "type": "line",
                "axis": "right",
                "account": "netIncome",
            },
        ],
        "options": {"unit": "원"},
        "xlSpan": 1,
        "help": "매출(막대·좌축) 과 영업이익·당기순이익(영역·우축) 별도 축. 우축이 좌축의 ~10% 스케일이라 이익 변동이 잘 보임. 매출 안정인데 이익 변동 크면 운영 레버리지 높음.",
    },
    # ─────────────────────────────────────────────────────────────
    # 4. 현금흐름 signed (영업+/투자-/재무- + 순현금증감 line)
    # ─────────────────────────────────────────────────────────────
    "cashflowSigned": {
        "kind": "trend",
        "title": "현금흐름",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [
            {
                "key": "cfOperating",
                "label": "영업활동",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "원",
                "type": "bar",
                "account": "cfOperating",
            },
            {
                "key": "cfInvesting",
                "label": "투자활동",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "account": "cfInvesting",
            },
            {
                "key": "cfFinancing",
                "label": "재무활동",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "account": "cfFinancing",
            },
            {
                "key": "netChange",
                "label": "순현금증감",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "원",
                "type": "line",
                "axis": "right",
                "compose": {"cfOperating": 1, "cfInvesting": 1, "cfFinancing": 1},
            },
        ],
        "options": {"unit": "원", "signed": True},
        "xlSpan": 1,
        "help": "정상 패턴: 영업+ / 투자- / 재무- (성숙기 기업). 영업CF 가 음수면 사업 자체로 현금 못 만드는 위험 신호. 투자+ 는 자산 매각, 재무+ 는 차입 증가 (성장기 또는 자금 부족).",
    },
    # ─────────────────────────────────────────────────────────────
    # 5. 이익률 (매출총이익률 / 영업이익률 / 순이익률)
    # ─────────────────────────────────────────────────────────────
    "marginTrend": {
        "kind": "trend",
        "title": "이익률 추세",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "gpm",
                "label": "매출총이익률",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"grossProfit": 1}, "den": {"revenue": 1}, "scale": 100},
            },
            {
                "key": "opm",
                "label": "영업이익률",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"operatingIncome": 1}, "den": {"revenue": 1}, "scale": 100},
            },
            {
                "key": "npm",
                "label": "순이익률",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"revenue": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%", "referenceBand": True},
        "xlSpan": 1,
        "help": "매출총이익률 = 원가 대비 가격결정력 (산업/제품 경쟁력). 영업이익률 = 비용 통제 능력. 순이익률 = 금융비용·세금 차감 후 최종. 추세 하락은 경쟁 심화 또는 비용 증가. (5y range 띠 표시 — P-DASH-V1 D12)",
    },
    # ─────────────────────────────────────────────────────────────
    # 6. 수익성 (ROE / ROA)
    # ─────────────────────────────────────────────────────────────
    "returnTrend": {
        "kind": "trend",
        "title": "수익성",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "roe",
                "label": "자기자본이익률",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"equity": 1}, "scale": 100},
            },
            {
                "key": "roa",
                "label": "총자산이익률",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"netIncome": 1}, "den": {"assets": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "xlSpan": 1,
        "help": "자기자본이익률 15%↑ 우수. 총자산이익률 과의 갭이 크면 부채 레버리지 효과 — 부채로 끌어올린 ROE 인지 확인 필요. ROE 가 ROA 와 가깝게 움직이면 무차입에 가까운 건전 수익성.",
    },
    # ─────────────────────────────────────────────────────────────
    # 7. 성장성 (매출/영업/순이익 YoY)
    # ─────────────────────────────────────────────────────────────
    "growthYoy": {
        "kind": "trend",
        "title": "성장성",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "revenueYoy",
                "label": "매출 증가율",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "%",
                "type": "bar",
                "yoy": "revenue",
            },
            {
                "key": "operatingYoy",
                "label": "영업이익 증가율",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "%",
                "type": "bar",
                "yoy": "operatingIncome",
            },
            {
                "key": "netIncomeYoy",
                "label": "순이익 증가율",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "%",
                "type": "bar",
                "yoy": "netIncome",
            },
        ],
        "options": {"unit": "%"},
        "xlSpan": 1,
        "help": "영업이익 증가율이 매출 증가율을 넘으면 마진 동반 성장 (질 좋은 성장). 매출만 늘고 이익 정체는 가격 인하 또는 비용 증가 신호. 음수 = 역성장.",
    },
    # ─────────────────────────────────────────────────────────────
    # 8. 비용 구조 stacked (매출원가/판관비/R&D/금융비용)
    # ─────────────────────────────────────────────────────────────
    "costStructureTrend": {
        "kind": "trend",
        "title": "비용 구조",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "costOfSales",
                "label": "매출원가",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "costOfSales",
            },
            {
                "key": "sga",
                "label": "판매관리비",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "sga",
            },
            {
                "key": "rnd",
                "label": "연구개발비",
                "color": COLORS[4],
                "intent": "neutral",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "rnd",
            },
            {
                "key": "financeCosts",
                "label": "금융비용",
                "color": COLORS[7],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "cost",
                "account": "financeCosts",
            },
        ],
        "options": {"stacked": True, "unit": "원"},
        "xlSpan": 1,
        "help": "매출원가 비중이 안정적인가가 핵심. 판관비 ↑↑ 는 영업 효율 악화 신호. R&D 비중 ↑ 는 미래 투자 의지. 금융비용 ↑ 는 차입 증가의 결과.",
    },
    # ─────────────────────────────────────────────────────────────
    # 9. 잉여현금흐름 (영업CF / CapEx / FCF + 영업CF/매출)
    # ─────────────────────────────────────────────────────────────
    "fcfTrend": {
        "kind": "trend",
        "title": "잉여현금흐름",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [
            {
                "key": "operating",
                "label": "영업현금흐름",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "원",
                "type": "bar",
                "account": "cfOperating",
            },
            {
                "key": "capex",
                "label": "자본적지출",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "account": "capex",
            },
            {
                "key": "fcf",
                "label": "잉여현금흐름",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "원",
                "type": "line",
                "compose": {"cfOperating": 1, "capex": -1},
            },
            {
                "key": "cfToRevenue",
                "label": "영업현금흐름/매출",
                "color": COLORS[6],
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "axis": "right",
                "ratio": {"num": {"cfOperating": 1}, "den": {"revenue": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "원"},
        "xlSpan": 1,
        "help": "잉여현금흐름 = 영업현금흐름 - 자본적지출. 지속 양수면 배당·자사주 여력. 영업현금흐름/매출 비율은 이익 품질 지표 — 회계 이익이 진짜 현금으로 들어오는지.",
    },
    # ─────────────────────────────────────────────────────────────
    # 10. 레버리지 (D/E + D/A + 유동비율)
    # ─────────────────────────────────────────────────────────────
    "leverageTrend": {
        "kind": "trend",
        "title": "레버리지",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "debtToEquity",
                "label": "부채자본비율",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"liabilities": 1}, "den": {"equity": 1}, "scale": 100},
            },
            {
                "key": "debtToAssets",
                "label": "부채자산비율",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"liabilities": 1}, "den": {"assets": 1}, "scale": 100},
            },
            {
                "key": "currentRatio",
                "label": "유동비율",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"currentAssets": 1}, "den": {"currentLiabilities": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "xlSpan": 1,
        "help": "부채자본비율 100% 미만 안정, 200% 이상 부담. 부채자산비율은 전체 자산 중 부채 비중. 유동비율은 단기 지급능력 (1 년 내 갚을 부채 대비 1 년 내 현금화 자산).",
    },
    # ─────────────────────────────────────────────────────────────
    # 11. 안정성 (부채비율 + 자기자본비율)
    # ─────────────────────────────────────────────────────────────
    "stabilityRatio": {
        "kind": "trend",
        "title": "안정성",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "debtRatio",
                "label": "부채비율",
                "color": COLORS[0],
                "intent": "negative",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"liabilities": 1}, "den": {"equity": 1}, "scale": 100},
            },
            {
                "key": "equityRatio",
                "label": "자기자본비율",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"equity": 1}, "den": {"assets": 1}, "scale": 100},
            },
        ],
        "options": {"unit": "%"},
        "xlSpan": 1,
        "help": "부채비율 100% 미만 = 자본이 부채보다 큼 (보수적 재무구조). 자기자본비율 50% 이상 = 자기자본 의존도 높음 (안정성). 두 지표는 같은 정보를 다른 각도로.",
    },
    # ─────────────────────────────────────────────────────────────
    # 12. 유동성 (유동/당좌/현금 비율 + 1.0/1.5 reference)
    # ─────────────────────────────────────────────────────────────
    "liquidityTrend": {
        "kind": "trend",
        "title": "유동성",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "currentRatio",
                "label": "유동비율",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"currentAssets": 1}, "den": {"currentLiabilities": 1}, "scale": 100},
            },
            {
                "key": "quickRatio",
                "label": "당좌비율",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"cash": 1, "receivables": 1}, "den": {"currentLiabilities": 1}, "scale": 100},
            },
            {
                "key": "cashRatio",
                "label": "현금비율",
                "color": COLORS[5],
                "intent": "accent",
                "unit": "%",
                "type": "line",
                "ratio": {"num": {"cash": 1}, "den": {"currentLiabilities": 1}, "scale": 100},
            },
        ],
        "options": {
            "unit": "%",
            "refLines": [
                {"value": 100, "label": "1.0", "intent": "neutral"},
                {"value": 150, "label": "1.5", "intent": "positive"},
            ],
        },
        "xlSpan": 1,
        "help": "유동비율 150% 이상이 안전선 (참조선). 당좌비율은 재고 제외한 보수적 지표 — 재고 안 팔려도 갚을 수 있는가. 현금비율은 가장 보수적 — 현금만으로 갚을 수 있는가.",
    },
    # ─────────────────────────────────────────────────────────────
    # 13. 활동성 (자산/재고/매출채권 회전율 — 회)
    # ─────────────────────────────────────────────────────────────
    "turnoverTrend": {
        "kind": "trend",
        "title": "활동성",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [
            {
                "key": "assetTurnover",
                "label": "자산회전율",
                "color": COLORS[2],
                "intent": "primary",
                "unit": "회",
                "type": "line",
                "ratio": {"num": {"revenue": 1}, "den": {"assets": 1}, "scale": 1},
            },
            {
                "key": "inventoryTurnover",
                "label": "재고회전율",
                "color": COLORS[3],
                "intent": "positive",
                "unit": "회",
                "type": "line",
                "ratio": {"num": {"costOfSales": 1}, "den": {"inventories": 1}, "scale": 1},
            },
            {
                "key": "receivableTurnover",
                "label": "매출채권회전율",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "회",
                "type": "line",
                "ratio": {"num": {"revenue": 1}, "den": {"receivables": 1}, "scale": 1},
            },
        ],
        "options": {"unit": "회"},
        "xlSpan": 1,
        "help": "자산회전율 = 매출 / 자산. 1 회면 자산 만큼 매출. 재고회전율 ↑ = 빠른 판매. 매출채권회전율 ↑ = 빠른 회수. 회전율 하락은 자산 효율 악화.",
    },
    # ─────────────────────────────────────────────────────────────
    # 14. 운전자본 (DSO / DIO — 일)
    #     DSO = (매출채권 / 매출) × 365, DIO = (재고 / 매출원가) × 365
    # ─────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────
    # 15. 수익·성장 KPI (개별 카드 4 — bento grid 한 row 채움)
    # ─────────────────────────────────────────────────────────────
    "kpiGrowthRevenue": {
        "kind": "kpiTile",
        "title": "매출",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [{"label": "매출", "account": "revenue", "unit": "원", "intent": "primary"}],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "최근 매출 + 전기 대비.",
    },
    "kpiGrowthOpIncome": {
        "kind": "kpiTile",
        "title": "영업이익",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [{"label": "영업이익", "account": "operatingIncome", "unit": "원", "intent": "positive"}],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "본업 수익성. 매출 대비 비율은 이익률 카드.",
    },
    "kpiGrowthNetIncome": {
        "kind": "kpiTile",
        "title": "순이익",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [{"label": "순이익", "account": "netIncome", "unit": "원", "intent": "primary"}],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "법인세·이자 차감 후 최종 이익.",
    },
    "kpiGrowthFcf": {
        "kind": "kpiTile",
        "title": "잉여현금흐름",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {"label": "FCF", "compose": {"cfOperating": 1, "capex": -1}, "unit": "원", "intent": "positive"}
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "영업CF − CapEx. 주주에게 돌려줄 수 있는 진짜 현금.",
    },
    # ─────────────────────────────────────────────────────────────
    # 16. 현금·배분 KPI (개별 카드 4)
    # ─────────────────────────────────────────────────────────────
    "kpiCashOp": {
        "kind": "kpiTile",
        "title": "영업CF",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [{"label": "영업CF", "account": "cfOperating", "unit": "원", "intent": "positive"}],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "본업이 만든 현금. 순이익과 차이는 발생주의/현금주의 gap.",
    },
    "kpiCashCapex": {
        "kind": "kpiTile",
        "title": "CapEx",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [{"label": "CapEx", "account": "capex", "unit": "원", "intent": "negative"}],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "유형자산 투자. 사업 확장 vs 유지보수 신호.",
    },
    "kpiCashFcf": {
        "kind": "kpiTile",
        "title": "FCF",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {"label": "FCF", "compose": {"cfOperating": 1, "capex": -1}, "unit": "원", "intent": "primary"}
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "영업CF − CapEx. 배당·자사주·부채상환 여력.",
    },
    "kpiCashFcfMargin": {
        "kind": "kpiTile",
        "title": "FCF/매출",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {
                    "label": "FCF/매출",
                    "ratio": {"num": {"cfOperating": 1, "capex": -1}, "den": {"revenue": 1}, "scale": 100},
                    "unit": "%",
                    "intent": "primary",
                }
            ],
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 1},
        "help": "매출 1 원당 FCF. 10%+ 우량.",
    },
    # ─────────────────────────────────────────────────────────────
    # P-DASH-V1 D10 — 성과 sub 깊이 보강.
    # DuPont 3-factor radar / 이익 지속성 gauge / M-Score gauge / 영업 레버리지 list.
    # ─────────────────────────────────────────────────────────────
    "dupontRadar": {
        "kind": "radar",
        "title": "DuPont 분해 (3-factor)",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        # duPontRadar adapter — 마지막 4 기간 polygon. 3 축 (NPM · Asset Turnover · Equity Multiplier) 동시 시계열.
        "dataSpec": {"adapter": "duPontRadar"},
        "options": {"unit": ""},
        "help": "ROE = NPM × Asset Turnover × Equity Multiplier. 마지막 4 기간 polygon 으로 축별 변동 추적.",
    },
    "earningsPersistenceGauge": {
        "kind": "gauge",
        "title": "이익 지속성 (영업CF/순이익)",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "kpiFromNorm",
            "tilePlans": [
                {
                    "label": "CF/NI",
                    "ratio": {"num": {"cfOperating": 1}, "den": {"netIncome": 1}, "scale": 100},
                    "unit": "%",
                    "intent": "primary",
                },
            ],
        },
        "options": {"unit": "%"},
        "help": "Penman Earnings Power — 영업CF/순이익. 100%↑ 정상 (이익=현금). 70% 미만 지속은 분식 의심.",
    },
    "operatingLeverageTopList": {
        "kind": "topList",
        "title": "영업 레버리지 신호",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "dupont",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "flagsTopList",
            "module": "dartlab.analysis.financial.earningsQuality",
            "fn": "calcEarningsQualityFlags",
        },
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 3},
        "help": "매출 변화 대비 영업이익·EBITDA 변화 — 고정비 비중 신호. Greenblatt Earnings Yield 보조.",
    },
    # ─────────────────────────────────────────────────────────────
    # 17-A. 자본배분 stacked bar over time (sankey 대체 — Wall Street Prep 정통).
    # ─────────────────────────────────────────────────────────────
    "capitalAllocationBars": {
        "kind": "trend",
        "title": "자본배분 (시간축)",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],  # adapter 가 series 직접 생성
        "dataSpec": {"adapter": "capitalAllocationBars"},
        "options": {"stacked": True, "unit": "원"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "연도별 영업CF 사용처 — 설비투자 / 배당 / 부채상환 / 잉여 4 분해. 비중 변화로 capital allocation 우선순위 추적.",
    },
    # ─────────────────────────────────────────────────────────────
    # 17-B. 자본배분 waterfall (단년 분해 — Damodaran "Returning Cash").
    # ─────────────────────────────────────────────────────────────
    "capitalAllocationWaterfall": {
        "kind": "waterfall",
        "title": "자본배분 (단년 분해)",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "quality",
        "seriesPlan": [],
        "dataSpec": {"adapter": "capitalAllocationWaterfall"},
        "options": {"unit": "원"},
        "layout": {"colSpan": 2, "rowSpan": 2},
        "help": "최근 기간 영업CF 가 어떻게 분해되는가. 영업CF → -설비투자 → -배당 → -부채상환 → 잉여. 부호별 색.",
    },
    # ─────────────────────────────────────────────────────────────
    # 18. 리스크·신호 — distress gauge
    # ─────────────────────────────────────────────────────────────
    "riskDistress": {
        "kind": "gauge",
        "title": "부실 위험 (Altman Z')",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {"adapter": "distressGauge"},
        "options": {},
        "layout": {"colSpan": 1, "rowSpan": 2},
        "help": "Altman Z' (private firm) 부실 예측. ≥2.9 안전 / 1.23~2.9 주의 / <1.23 위험.",
    },
    # ─────────────────────────────────────────────────────────────
    # 19. 리스크·신호 — 이상신호 top 6
    # ─────────────────────────────────────────────────────────────
    # 만기 분포 — 단기차입금 / 장기차입금·사채 stacked. McKinsey "Refinancing Risk".
    "maturityProfile": {
        "kind": "trend",
        "title": "부채 만기 분포",
        "topic": "BS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "shortDebt",
                "label": "단기차입금 (1년 내)",
                "color": COLORS[2],
                "intent": "negative",
                "unit": "원",
                "type": "bar",
                "stack": "maturity",
                "account": "shortDebt",
            },
            {
                "key": "longDebt",
                "label": "장기차입금·사채 (1년+)",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "원",
                "type": "bar",
                "stack": "maturity",
                "account": "longDebt",
            },
        ],
        "options": {"stacked": True, "unit": "원"},
        "help": "단기 비중 ↑ = 차환 위험 (refinancing risk). 금리 사이클 노출 신호. 만기 mismatch (단기 자금으로 장기 투자) 도 함께 확인.",
    },
    # 시나리오 민감도 heatmap — 매출 변동 × 마진 변동 9 cell matrix.
    "scenarioSensitivityHeatmap": {
        "kind": "matrix",
        "title": "시나리오 민감도 (매출 × 마진)",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {"adapter": "scenarioSensitivity"},
        "options": {},
        "help": "매출 ±X% × 영업이익률 ±Y% 변화에 따른 영업이익 변동 (단위 ±N%). Damodaran scenario analysis. 색 진하기 = 절대값 크기.",
    },
    "riskDistressDecomp": {
        "kind": "topList",
        "title": "부실 위험 분해 (Altman Z' 5 인자)",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {"adapter": "distressDecomp"},
        "options": {},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "Altman Z' 점수가 왜 그 값인지 — 5 인자 각각의 값 + 가중 기여도. 절대값 큰 인자가 점수 결정. P-DASH-V1 D13 decompositionPanel.",
    },
    "riskAnomaly": {
        "kind": "topList",
        "title": "변동 큰 지표",
        "topic": "ratios",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {
            "adapter": "flagsTopList",
            "module": "dartlab.analysis.financial.earningsQuality",
            "fn": "calcEarningsQualityFlags",
        },
        "options": {},
        "layout": {"colSpan": 2, "rowSpan": 3},
        "help": "전년 대비 변동 큰 지표 top 6 (절대 변동값 기준). DSO/DIO/마진/레버리지 동향.",
    },
    # ─────────────────────────────────────────────────────────────
    # 20. 리스크·신호 — phaseIndicator (생애주기)
    # ─────────────────────────────────────────────────────────────
    "riskLifeCycle": {
        "kind": "phaseIndicator",
        "title": "생애주기 단계",
        "topic": "CF",
        "tab": "financial",
        "subCategory": "snowflake",
        "seriesPlan": [],
        "dataSpec": {"adapter": "lifeCyclePhase"},
        "options": {},
        "layout": {"colSpan": 4, "rowSpan": 1},
        "help": "CF 3축 부호 + 매출 성장률로 6 단계 (도입·성장·성숙Ⅰ·성숙Ⅱ·쇠퇴·회복) 추정.",
    },
    "workingCapitalDays": {
        "kind": "trend",
        "title": "운전자본",
        "topic": "IS",
        "tab": "financial",
        "subCategory": "credit",
        "seriesPlan": [
            {
                "key": "dso",
                "label": "매출채권회수일수",
                "color": COLORS[1],
                "intent": "accent",
                "unit": "일",
                "type": "line",
                "ratio": {"num": {"receivables": 365}, "den": {"revenue": 1}, "scale": 1},
            },
            {
                "key": "dio",
                "label": "재고자산회수일수",
                "color": COLORS[6],
                "intent": "neutral",
                "unit": "일",
                "type": "line",
                "ratio": {"num": {"inventories": 365}, "den": {"costOfSales": 1}, "scale": 1},
            },
        ],
        "options": {"unit": "일"},
        "xlSpan": 1,
        "help": "매출채권회수일수 + 재고자산회수일수 = 현금주기 (운전자본 묶이는 기간). 짧을수록 좋다. 늘어나면 운전자본 부담 증가 — 매출은 늘어도 현금은 안 들어옴.",
    },
}
"""재무제표 dashboard 14 카드. 모든 series 가 catalog 의 SeriesPlan 만으로 정의 — statements/ratios 함수 호출 없음."""


FINANCE_DASHBOARD_KEYS: list[str] = [
    # row 1: 핵심 KPI 4 개 분리 카드 (1×1 × 4 = 한 row)
    "kpiRevenue",
    "kpiOperatingIncome",
    "kpiRoe",
    "kpiDebtRatio",
    # row 2: 자산구조 (2×3) + 부채상세 (1×3) + 자본상세 (1×3)
    "assetComposition",
    "liabilityDetail",
    "equityDetail",
    # row 3+: 손익구조 (2×2) + 현금흐름 (2×2) + 이익률 (2×2) + 매출 YoY (2×2)
    "incomeBreakdown",
    "cashflowSigned",
    "marginTrend",
    "growthYoy",
    # 수익·성장 sub (4 KPI + 매출/이익 시계열)
    "kpiGrowthRevenue",
    "kpiGrowthOpIncome",
    "kpiGrowthNetIncome",
    "kpiGrowthFcf",
    "returnTrend",
    "turnoverTrend",
    "costStructureTrend",
    # 현금·배분 sub (4 KPI + sankey + FCF)
    "kpiCashOp",
    "kpiCashCapex",
    "kpiCashFcf",
    "kpiCashFcfMargin",
    "dupontRadar",
    "earningsPersistenceGauge",
    "operatingLeverageTopList",
    "capitalAllocationBars",
    "capitalAllocationWaterfall",
    "fcfTrend",
    # 재무건전성 sub
    "leverageTrend",
    "stabilityRatio",
    "liquidityTrend",
    "workingCapitalDays",
    "maturityProfile",
    # 리스크·신호 sub
    "riskDistress",
    "riskDistressDecomp",
    "scenarioSensitivityHeatmap",
    "riskAnomaly",
    "riskLifeCycle",
]
"""dashboard 카드 노출 순서 — bento 밀도 packing 기준.
KPI 1×1 4 개 = 한 row, 자산구조 2×3 + 부채/자본 1×3 = 한 row, trend 2×2 4 개 = 두 row."""


# overview = "한눈에 진단" narrative — 38 카드 dump 가 아닌 12 카드 curated.
# 순서: KPI 4 → 회계 등식 hero → 본업+현금 → 추세 → 위험.
OVERVIEW_KEYS: list[str] = [
    # row 1: 핵심 KPI 4 (각 1×1) — 매출·영업이익·ROE·부채비율
    "kpiRevenue",
    "kpiOperatingIncome",
    "kpiRoe",
    "kpiDebtRatio",
    # row 2-5: 자산구조 dual-stack hero (4×4)
    "assetComposition",
    # row 6+: 본업 + 현금 (각 2×3)
    "incomeBreakdown",
    "cashflowSigned",
    # row 추세 (각 2×3)
    "marginTrend",
    "growthYoy",
    # row 위험 (gauge 1×2 + topList 2×3 + 생애주기 4×1)
    "riskDistress",
    "riskAnomaly",
    "riskLifeCycle",
]
"""overview narrative — '5초 진단' curated 12 카드.
사용자 요구 (P-DASH-V1 보강 2): 흐름 view 지 sub 의 dump 가 아니다."""


__all__ = ["FINANCE_CARDS", "FINANCE_DASHBOARD_KEYS", "OVERVIEW_KEYS"]
