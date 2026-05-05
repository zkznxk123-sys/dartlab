"""
실험 ID: 002
실험명: DART↔EDGAR snakeId 정렬 분석

목적:
- EDGAR 179개 표준계정의 snakeId와 DART의 snakeId 체계 비교
- L2 엔진(insight, rank)이 소스 무관하게 동작하려면 snakeId가 일치해야 함
- 불일치 항목을 식별하고 정렬 전략 수립

가설:
1. BS/IS/CF 핵심 계정(~30개)은 이미 일치할 것이다
2. EDGAR 전용 세부 계정(NT, CI)은 DART에 대응 없을 것이다
3. 네이밍 컨벤션 차이 (DART: IFRS 기반, EDGAR: US-GAAP 기반)가 주요 불일치 원인

방법:
1. DART의 canonical snakeId 전체 목록 수집 (CORE_MAP values + SNAKE_ALIASES canonicals)
2. EDGAR의 179개 snakeId 전체 목록 수집
3. 교집합(일치) / DART only / EDGAR only 분류
4. L2 엔진이 실제 사용하는 snakeId 목록과 교차 검증
5. 불일치 항목에 대한 alias 매핑 테이블 제안

결과 (실험 후 작성):
- EDGAR 전체 179개, DART canonical 31개, L2 사용 29개
- 양쪽 일치: 13개 (revenue, net_income, total_assets, total_equity 등)
- L2 호환: 13/29 (45%) — 16개 EDGAR에 없음 (alias로 해결 가능)
- EDGAR only: 166개 (대부분 세부 계정, NT/CI/EQ 전용)
- DART only: 18개 (IFRS 특화 계정)
- alias 필요 13개: CF 소계 3, BS 비유동 2, IS 계정 2, BS 자산 6
- 구조적 차이 2개: equity (GAAP vs IFRS NCI 처리), bonds (EDGAR는 long_term_debt에 포함)

결론:
- 가설 1 부분 채택: 핵심 계정 13개 일치하나 30개에는 못 미침 (네이밍 차이 때문)
- 가설 2 채택: NT/CI/EQ 세부 계정은 DART에 대응 없음
- 가설 3 채택: 16개 불일치 중 13개가 순수 네이밍 차이 (alias로 해결)
- EDGAR SNAKE_ALIASES 테이블 13개로 L2 호환성 확보 가능
- 자본 구조 차이는 매핑 단계에서 total_equity↔equity_including_nci 스왑 필요

실험일: 2026-03-09
"""


EDGAR_SNAKE_IDS = {
    "BS": [
        "total_assets", "current_assets", "cash_and_equivalents",
        "short_term_investments", "accounts_receivable", "inventory",
        "prepaid_expenses", "other_current_assets", "noncurrent_assets",
        "long_term_investments", "property_plant_equipment", "goodwill",
        "intangible_assets", "deferred_tax_assets", "other_noncurrent_assets",
        "total_liabilities", "current_liabilities", "accounts_payable",
        "accrued_expenses", "short_term_debt", "deferred_revenue_current",
        "other_current_liabilities", "noncurrent_liabilities", "long_term_debt",
        "deferred_tax_liabilities", "deferred_revenue_noncurrent",
        "other_noncurrent_liabilities", "total_equity", "common_stock",
        "additional_paid_in_capital", "retained_earnings", "treasury_stock",
        "accumulated_other_comprehensive_income", "product_warranty_accrual",
        "other_receivables_current", "unrecognized_tax_benefits",
        "commercial_paper_liability", "debt_carrying_amount",
        "accrued_income_taxes_current", "equity_method_investments",
        "operating_lease_liability_noncurrent", "operating_lease_liability_current",
        "operating_lease_rou_asset", "noncontrolling_interest",
        "redeemable_noncontrolling_interest", "finance_lease_liability_noncurrent",
        "capital_lease_current", "income_taxes_receivable",
        "accumulated_depreciation", "restricted_cash_current",
        "restricted_cash_noncurrent", "contract_liability",
        "restructuring_reserve", "notes_loans_receivable_current",
    ],
    "IS": [
        "revenue", "cost_of_revenue", "gross_profit", "operating_expenses",
        "research_development", "selling_general_admin",
        "depreciation_amortization", "other_operating_expenses",
        "operating_income", "interest_expense", "interest_income",
        "other_income_expense", "income_before_tax", "income_tax_expense",
        "net_income", "basic_eps", "diluted_eps", "basic_shares",
        "diluted_shares", "dividends_per_share",
        "other_comprehensive_income", "comprehensive_income",
        "foreign_currency_translation", "securities_valuation_oci",
        "unrealized_holding_gain_loss", "derivative_hedge_oci",
        "incremental_diluted_shares", "fx_gain_loss",
        "dividends_common_stock", "eps_continuing_operations",
        "comprehensive_income_nci", "eps_basic_and_diluted",
        "advertising_expense", "marketing_expense",
        "stock_compensation_expense", "defined_contribution_cost",
        "cost_of_services", "goodwill_impairment",
        "restructuring_charges", "asset_impairment_charges",
        "net_income_including_nci", "gain_loss_investments",
    ],
    "CF": [
        "operating_cash_flow", "net_income_cf", "depreciation_cf",
        "stock_compensation", "deferred_taxes", "working_capital_changes",
        "investing_cash_flow", "capex", "acquisitions",
        "investment_purchases", "investment_sales", "financing_cash_flow",
        "debt_repayment", "debt_issuance", "stock_repurchase",
        "dividends_paid", "stock_issuance", "fx_effect",
        "net_change_in_cash", "beginning_cash", "ending_cash",
        "free_cash_flow", "inventory_change",
        "other_operating_assets_change", "other_operating_liabilities_change",
        "accounts_payable_change", "accounts_receivable_change",
        "other_investing_activities", "investment_maturities",
        "other_receivables_change", "tax_withholding_stock_compensation",
        "stock_compensation_tax_benefit", "commercial_paper_net",
        "deferred_revenue_change", "afs_securities_purchases",
        "afs_securities_sales", "intangible_assets_acquisition",
        "other_noncash_items", "productive_assets_acquisition",
        "excess_tax_benefit_financing", "other_financing_activities",
        "other_noncurrent_liabilities_change", "prepaid_expenses_change",
        "accrued_liabilities_change", "cash_period_change_legacy",
        "finance_lease_principal", "long_term_debt_repayment",
        "operating_lease_payments", "debt_discount_amortization",
        "gain_loss_ppe_sale", "bad_debt_provision",
        "income_taxes_paid", "restructuring_payments",
    ],
    "EQ": [
        "total_equity_change", "cumulative_effect_accounting_change",
        "dividends_declared", "nci_business_combination",
        "equity_reclassification", "other_equity_adjustments",
    ],
    "CI": [
        "total_other_comprehensive_income", "foreign_currency_translation_tax",
        "afs_securities_tax", "other_comprehensive_income_detail",
    ],
    "NT": [
        "derivative_assets_detail", "derivative_liabilities_detail",
        "derivative_other_detail", "fair_value_measurement_detail",
        "lease_receivable_schedule", "lease_investment_detail",
        "stock_option_detail", "stock_comp_assumptions",
        "warrant_detail", "tax_adjustment_detail",
        "deferred_tax_detail", "held_to_maturity_detail",
        "afs_securities_detail", "equity_method_investment_detail",
        "securities_collateral_detail", "acquisition_detail",
        "restructuring_detail", "property_detail",
        "debt_instrument_detail", "other_note_detail",
    ],
}

DART_CORE_MAP_VALUES = {
    "revenue", "cost_of_sales", "gross_profit", "operating_income",
    "net_income", "total_assets", "current_assets", "non_current_assets",
    "cash_and_equivalents", "total_liabilities", "current_liabilities",
    "non_current_liabilities", "short_term_borrowings", "long_term_borrowings",
    "bonds", "equity_including_nci", "total_equity",
    "operating_cashflow", "investing_cashflow", "financing_cashflow",
    "inventories",
}

DART_SNAKE_ALIASES_CANONICALS = {
    "revenue", "net_income", "total_equity", "non_current_assets",
    "non_current_liabilities", "equity_nci", "total_equity_and_liabilities",
    "income_tax_expense", "profit_before_tax", "basic_eps", "diluted_eps",
    "short_term_borrowings", "long_term_borrowings", "bonds",
    "cash_and_equivalents", "current_portion_ltb", "issued_capital",
    "ppe", "operating_cashflow", "investing_cashflow", "financing_cashflow",
    "trade_receivables",
}

DART_ALL_CANONICAL = DART_CORE_MAP_VALUES | DART_SNAKE_ALIASES_CANONICALS

L2_INSIGHT_USED = {
    "revenue", "operating_income", "net_income", "total_assets",
    "current_assets", "non_current_assets", "total_liabilities",
    "current_liabilities", "non_current_liabilities", "total_equity",
    "equity_including_nci", "cash_and_equivalents", "inventories",
    "trade_receivables", "short_term_borrowings", "long_term_borrowings",
    "bonds", "operating_cashflow", "investing_cashflow", "financing_cashflow",
    "cost_of_sales", "gross_profit", "profit_before_tax",
    "income_tax_expense", "basic_eps", "diluted_eps", "ppe",
    "issued_capital", "equity_nci",
}


def analyze():
    edgarAll = set()
    for stmt, ids in EDGAR_SNAKE_IDS.items():
        edgarAll.update(ids)

    print("=== snakeId 체계 비교 ===")
    print(f"  EDGAR 전체: {len(edgarAll)}")
    print(f"  DART canonical: {len(DART_ALL_CANONICAL)}")
    print(f"  L2 insight 사용: {len(L2_INSIGHT_USED)}")

    matched = edgarAll & DART_ALL_CANONICAL
    edgarOnly = edgarAll - DART_ALL_CANONICAL
    dartOnly = DART_ALL_CANONICAL - edgarAll

    print(f"\n--- 일치 (양쪽 동일): {len(matched)} ---")
    for sid in sorted(matched):
        print(f"  {sid}")

    print(f"\n--- EDGAR only (DART에 없음): {len(edgarOnly)} ---")
    for sid in sorted(edgarOnly):
        stmts = [s for s, ids in EDGAR_SNAKE_IDS.items() if sid in ids]
        print(f"  {sid}  [{'/'.join(stmts)}]")

    print(f"\n--- DART only (EDGAR에 없음): {len(dartOnly)} ---")
    for sid in sorted(dartOnly):
        print(f"  {sid}")

    print("\n=== L2 호환성 분석 ===")
    l2InEdgar = L2_INSIGHT_USED & edgarAll
    l2NotInEdgar = L2_INSIGHT_USED - edgarAll
    print(f"  L2가 사용하는 snakeId 중 EDGAR에 있는 것: {len(l2InEdgar)}/{len(L2_INSIGHT_USED)}")

    if l2NotInEdgar:
        print("\n  L2에서 쓰지만 EDGAR에 없는 snakeId:")
        for sid in sorted(l2NotInEdgar):
            print(f"    {sid}")

    print("\n=== 네이밍 차이 후보 (동일 개념, 다른 이름) ===")
    namingDiffs = [
        ("DART: operating_cashflow", "EDGAR: operating_cash_flow", "CF 소계"),
        ("DART: investing_cashflow", "EDGAR: investing_cash_flow", "CF 소계"),
        ("DART: financing_cashflow", "EDGAR: financing_cash_flow", "CF 소계"),
        ("DART: non_current_assets", "EDGAR: noncurrent_assets", "BS 비유동자산"),
        ("DART: non_current_liabilities", "EDGAR: noncurrent_liabilities", "BS 비유동부채"),
        ("DART: cost_of_sales", "EDGAR: cost_of_revenue", "IS 매출원가"),
        ("DART: inventories", "EDGAR: inventory", "BS 재고자산"),
        ("DART: ppe", "EDGAR: property_plant_equipment", "BS 유형자산"),
        ("DART: profit_before_tax", "EDGAR: income_before_tax", "IS 세전이익"),
        ("DART: short_term_borrowings", "EDGAR: short_term_debt", "BS 단기차입금"),
        ("DART: long_term_borrowings", "EDGAR: long_term_debt", "BS 장기차입금"),
        ("DART: trade_receivables", "EDGAR: accounts_receivable", "BS 매출채권"),
        ("DART: equity_nci", "EDGAR: noncontrolling_interest", "BS 비지배지분"),
        ("DART: equity_including_nci", "(EDGAR 없음 — total_equity가 NCI 포함?)", "BS 자본총계"),
        ("DART: bonds", "(EDGAR 없음 — long_term_debt에 포함?)", "BS 사채"),
    ]
    for dart, edgar, desc in namingDiffs:
        print(f"  {desc}")
        print(f"    {dart}")
        print(f"    {edgar}")
        print()

    print("=== 정렬 전략 제안 ===")
    print("""
  1. EDGAR→DART alias 테이블 구축
     - operating_cash_flow → operating_cashflow
     - investing_cash_flow → investing_cashflow
     - financing_cash_flow → financing_cashflow
     - noncurrent_assets → non_current_assets
     - noncurrent_liabilities → non_current_liabilities
     - cost_of_revenue → cost_of_sales
     - inventory → inventories
     - property_plant_equipment → ppe
     - income_before_tax → profit_before_tax
     - short_term_debt → short_term_borrowings
     - long_term_debt → long_term_borrowings
     - accounts_receivable → trade_receivables
     - noncontrolling_interest → equity_nci

  2. DART canonical을 기준으로 통일
     - L2 엔진은 DART canonical만 사용
     - EDGAR 엔진은 자체 매핑 후 alias 적용하여 DART canonical로 변환
     - 즉 EDGAR의 SNAKE_ALIASES가 위 테이블이 됨

  3. EDGAR 전용 세부 계정 (NT, CI, EQ)
     - L2에서 사용하지 않으므로 당장 정렬 불필요
     - EDGAR Company에서만 접근 가능하게 유지

  4. 자본 구조 차이 (IFRS vs US-GAAP)
     - DART: equity_including_nci (자본총계) / total_equity (지배기업 귀속)
     - EDGAR: total_equity (NCI 포함 자본총계)
     - → EDGAR의 total_equity를 equity_including_nci로 매핑하고,
       StockholdersEquity를 total_equity(지배기업 귀속)로 매핑
""")


if __name__ == "__main__":
    analyze()
