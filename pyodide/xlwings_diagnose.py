# xlwings Lite 에서 c.show("IS") 가 CIS 반환하는 원인 진단 셀.
# 이 셀 전체를 xlwings Lite notebook 에 붙여넣고 Run Cell.
# 출력된 내용을 그대로 복사해서 알려주세요.
#
# 각 단계별로 어디서 finance parquet 로딩이 실패해 docs fallback 으로 빠지는지 짚어냅니다.

import sys
print(f"[0] sys.platform = {sys.platform}")

# ── 1. pyodide 환경 & JSPI 지원 여부 ──
try:
    import pyodide
    print(f"[1] pyodide version: {pyodide.__version__}")
except ImportError:
    print("[1] pyodide 모듈 import 실패")

try:
    from pyodide.ffi import run_sync  # noqa
    print("[1] JSPI run_sync: 사용 가능")
except ImportError:
    print("[1] JSPI run_sync: 없음 (Chrome 137+ / JSPI 필요)")

try:
    from js import XMLHttpRequest  # noqa
    print("[1] XMLHttpRequest: 사용 가능")
except Exception as e:
    print(f"[1] XMLHttpRequest: 없음 ({type(e).__name__})")

# ── 2. dartlab 버전 확인 ──
import dartlab
print(f"[2] dartlab.__version__ = {dartlab.__version__}")

# ── 3. Company 생성 + 어떤 경로가 동작하는지 ──
STOCK = "005930"

import warnings
warnings.filterwarnings("always")

c = dartlab.Company(STOCK)
print(f"[3] Company 생성 OK. corpName={c.corpName!r}")
print(f"    _hasDocs={c._hasDocs}  _hasFinanceParquet={c._hasFinanceParquet}  _hasReport={c._hasReport}")

# ── 4. buildTimeseries 직접 호출 — finance parquet 로딩 + 파싱 한 번에 검증 ──
try:
    from dartlab.providers.dart.finance.pivot import buildTimeseries
    ts = buildTimeseries(STOCK)
    if ts is None:
        print("[4] buildTimeseries: None 반환 (← docs fallback 의 원인)")
    else:
        series, periods = ts
        print(f"[4] buildTimeseries OK: periods={len(periods)}, sjDivs={list(series.keys())}")
        print(f"    IS 계정 수: {len(series.get('IS', {}))} (정상이면 30개 내외)")
        print(f"    periods 샘플: {periods[:3]}...{periods[-3:]}")
except Exception as e:
    import traceback
    print(f"[4] buildTimeseries 예외: {type(e).__name__}: {e}")
    traceback.print_exc()

# ── 5. finance parquet 파일이 FS 에 내려왔는지 (buildTimeseries 이후) ──
from pathlib import Path
finPath = Path(f"/data/dart/finance/{STOCK}.parquet")
print(f"[5] finance parquet 존재: {finPath.exists()}")
if finPath.exists():
    size = finPath.stat().st_size
    magic = finPath.read_bytes()[:4]
    print(f"    크기 {size} bytes, magic {magic!r} (정상이면 b'PAR1')")

# ── 6. pyarrow 직접 읽기 + schema ──
if finPath.exists():
    try:
        import pyarrow.parquet as pq
        import io
        table = pq.read_table(io.BytesIO(finPath.read_bytes()))
        print(f"[6] pyarrow OK: rows={table.num_rows}")
        sj_col = "sj_div"
        if sj_col in table.column_names:
            sj_unique = table[sj_col].to_pylist()
            print(f"    sj_div unique: {sorted(set(sj_unique))}")
        yr_col = "bsns_year"
        if yr_col in table.column_names:
            idx = table.column_names.index(yr_col)
            print(f"    bsns_year arrow type: {table.schema[idx].type}")
    except Exception as e:
        print(f"[6] pyarrow 실패: {type(e).__name__}: {e}")

# ── 7. polars 변환 후 필터 동작 검증 ──
if finPath.exists():
    try:
        import polars as pl
        df = pl.from_arrow(table)
        print(f"[7] polars shape={df.shape}")
        if "bsns_year" in df.columns:
            print(f"    bsns_year polars dtype: {df.schema['bsns_year']}")
        if "sj_div" in df.columns:
            filtered = df.filter(pl.col("sj_div").is_in(["BS", "IS", "CIS", "CF"]))
            print(f"    sj_div filter 후 rows: {filtered.shape[0]}")
        if "bsns_year" in df.columns:
            yrFiltered = df.filter(pl.col("bsns_year") != "2015")
            print(f"    bsns_year != '2015' 후 rows: {yrFiltered.shape[0]}")
    except Exception as e:
        print(f"[7] polars 실패: {type(e).__name__}: {e}")

# ── 8. c.show("IS") 최종 결과 ──
print(f"[8] _hasFinance: {c._hasFinance}, _hasFinanceParquet: {c._hasFinanceParquet}")
df_is = c.show("IS")
if df_is is not None:
    print(f"[9] c.show('IS') shape={df_is.shape}")
    print(f"    columns: {df_is.columns[:8]}")
    print(f"    항목 샘플: {df_is['항목'].head(5).to_list() if '항목' in df_is.columns else 'N/A'}")
    # 정상 IS 인지 확인 — 매출액 존재 여부가 결정적
    if '항목' in df_is.columns:
        items = df_is['항목'].to_list()
        has_sales = any('매출액' in i or 'sales' in i.lower() for i in items if i)
        has_op = any('영업이익' in i for i in items if i)
        col_is_quarterly = any('Q' in c for c in df_is.columns)
        verdict = "✅ 정상 IS (finance parquet 경로)" if has_sales and has_op and col_is_quarterly else "❌ docs fallback (finance parquet 로딩 실패)"
        print(f"    판정: {verdict}")
        print(f"    (매출액={has_sales}, 영업이익={has_op}, 분기컬럼={col_is_quarterly})")
else:
    print("[9] c.show('IS') = None")
