"""Deterministic driver node definitions for the L2.5 scenario engine (born-clean).

Per `mainPlan/scenario-simulator/01-engine-architecture.md` §5 (the node table) and §6 (the
executor contract), this module holds the deterministic (lens=None) driver nodes and the function
that builds a `DriverSheet` for one scenario. Each node is one of two kinds (§2):

- a thin call into an L2 leaf (`proforma` -> `analysis.financial.proforma.buildProforma`), or
- the single owned macro->fundamentals edge (`rev.path` -> `simulate.transfer`), plus the preset
  pass-through (`macro.path`) and a minimal FCFF discount off the proforma path (`dcf`).

Node graph (deterministic minimum set, §5):

    macro.path (preset gdp/rate/fx for the scenario; no deps)
      -> rev.path (transferRevenuePath over base revenue/margin + sector elasticity)
        -> proforma (buildProforma L2 leaf over the growth path derived from rev.path)
          -> dcf (FCFF discount off the proforma FCF path + WACC)

Every registry fn matches the `evaluateSheet` contract:
``fn(node, sheet, depValues) -> (value, vector, provenance, refs, frozenInputs, asOf, latestAsOf)``.

Snapshot discipline (§13b-5): the company's base metrics (revenue / margin / shares / sector
elasticity / WACC / net debt) are read ONCE into the sheet snapshot by `buildSnapshot` before
evaluation; no node reloads data mid-eval, so a re-run is byte-identical.

honest-gap (§3): a missing leaf or absent base metric yields a node value of None (never 0); the
caller (`run.py`) reads that as a `partial` quality status.

Born-clean (§10): this module does NOT import the legacy simulation flow
(`analysis/forecast/simulation.py`, `_applyMacroShock`, `_simScenario`). It imports forward only:
L0 (`core.utils.extract`), L1.5 (`synth.scenario`), and L2 leafs
(`analysis.financial.proforma.buildProforma`, the `analysis.financial._valuationHelpers` sector /
series / shares accessors). The FCFF discount in the `dcf` node is a faithful port of the legacy
terminal-value formula, re-derived here so the `dcf` node reflects THIS scenario's proforma FCF.

Layer: L2.5. Forward imports: L0 (core), L1.5 (synth), L2 (analysis.financial).
"""

from __future__ import annotations

from typing import Any

from dartlab.analysis.financial._valuationHelpers import (
    _getSeriesAndShares,
    _resolveSectorKey,
)
from dartlab.analysis.financial.proforma import buildProforma
from dartlab.core.utils.extract import getLatest, getTTM
from dartlab.simulate.sheet import DriverNode, DriverSheet
from dartlab.synth.scenario import (
    DEFAULT_ELASTICITY,
    SectorElasticity,
    getElasticity,
    getPresetScenarios,
)

# Registry fn keys (one per driverId). The DriverNode.fn dispatch keys the sheet registry.
_FN_MACRO = "simulate.macroPath"
_FN_REV = "simulate.revPath"
_FN_PROFORMA = "simulate.proforma"
_FN_DCF = "simulate.dcf"

# Driver ids (§5 node table).
DRIVER_MACRO = "macro.path"
DRIVER_REV = "rev.path"
DRIVER_PROFORMA = "proforma"
DRIVER_DCF = "dcf"

_DEFAULT_BASE_WACC = 10.0  # legacy baseWacc default when sectorParams.discountRate is absent.
_DEFAULT_MARGIN = 10.0  # legacy fallback when operating margin is unavailable.
_TAX_RATE = 0.22  # legacy KR corporate effective-rate default for the FCFF proxy.
_TERMINAL_GROWTH_CAP = 3.0  # legacy terminal growth cap.


def _baseMetrics(series: dict) -> dict[str, float | None]:
    """Extract the base revenue / margin / net debt the simulate snapshot needs (born-clean).

    Capabilities:
        Reads the minimal base metrics the driver DAG consumes — TTM revenue, operating margin,
        and net debt — directly from a finance series using L0 extract helpers. Replicates the
        same accounts the legacy `_extractBaseMetrics` reads (sales/operating_profit and the
        debt/cash balance-sheet lines) without importing the legacy simulation flow.

    Args:
        series: a finance series dict (``{sjDiv: {account: [..]}}``) as built by
            ``Company._buildFinanceSeries`` / ``_getSeriesAndShares``.

    Returns:
        dict[str, float | None]: ``{"revenue", "margin", "netDebt"}``. ``revenue`` / ``margin``
        are None when the underlying accounts are absent (honest-gap, never 0); ``netDebt``
        defaults to 0.0 when the debt/cash lines are absent.

    Raises:
        None — every lookup is None-tolerant.

    Example:
        >>> _baseMetrics({"IS": {"sales": [None]}})["revenue"] is None
        True

    Requires:
        L0 ``getTTM`` / ``getLatest`` (no dartlab analysis import).
    """
    rev = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")
    oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
    margin = (oi / rev * 100) if rev and oi and rev > 0 else None

    cash = getLatest(series, "BS", "cash_and_cash_equivalents") or 0.0
    stb = getLatest(series, "BS", "shortterm_borrowings") or 0.0
    ltb = getLatest(series, "BS", "longterm_borrowings") or 0.0
    bonds = getLatest(series, "BS", "debentures") or 0.0
    netDebt = stb + ltb + bonds - cash

    return {"revenue": rev, "margin": margin, "netDebt": netDebt}


def buildSnapshot(company: Any, *, asOf: str | None = None) -> dict:
    """Read a company's frozen base metrics ONCE into a simulate snapshot (§13b-5).

    Capabilities:
        Loads the read-once inputs the deterministic driver DAG consumes — the finance series,
        base revenue / operating margin / net debt, shares outstanding, sector elasticity, and
        base WACC — into a flat dict the registry fns read during evaluation. After this call no
        node reloads data, so an `evaluateSheet` re-run over the snapshot is byte-identical.

    Args:
        company: a `Company` (DART/EDGAR) instance. Read forward via the L2
            `_getSeriesAndShares` / `_resolveSectorKey` accessors and `sectorParams`.
        asOf: an explicit data-vintage label to stamp on every node. When None, falls back to the
            company's latest finance period (or ``"latest"`` if unavailable).

    Returns:
        dict: the snapshot with keys ``series`` (dict | None), ``baseRevenue`` (float | None),
        ``baseMargin`` (float | None), ``netDebt`` (float), ``shares`` (int | None),
        ``elasticity`` (SectorElasticity), ``sectorKey`` (str | None), ``baseWacc`` (float),
        ``asOf`` (str), ``latestAsOf`` (str). Missing accounts leave revenue/margin None
        (honest-gap), never 0.

    Raises:
        None — every accessor is failure-tolerant; absence becomes a None field, not an error.

    Example:
        >>> snap = buildSnapshot(Company("005930"))  # doctest: +SKIP
        >>> set(snap) >= {"series", "baseRevenue", "elasticity", "shares"}  # doctest: +SKIP
        True

    Guide:
        Build the snapshot once per `runScenario`; reuse it across the per-scenario sheet so the
        elasticity / base metrics are identical for baseline vs adverse (only the macro path
        differs). Read by the registry fns, never mutated during evaluation.

    SeeAlso:
        - ``buildScenarioSheet``: wires a `DriverSheet` over this snapshot.
        - ``dartlab.analysis.financial._valuationHelpers._getSeriesAndShares``: series + shares.
        - ``dartlab.synth.scenario.getElasticity``: sector-key -> elasticity.

    Requires:
        A `Company` exposing `_buildFinanceSeries`, `sector`, and `sectorParams`.

    AIContext:
        The snapshot is frozen assumptions, not a forecast — surface `sectorKey`, `elasticity`,
        and `asOf` so the scenario is auditable; a None revenue means "data absent", not zero.

    LLM Specifications:
        AntiPatterns:
            - Re-reading the company inside a node fn — breaks snapshot determinism (§13b-5).
            - Treating a None baseRevenue as 0 — it is an honest data gap.
        OutputSchema: ``dict`` with the keys listed under Returns.
        Prerequisites: a constructed `Company`.
        Freshness: inherits the company's latest finance period as `asOf`/`latestAsOf`.
        Dataflow: company -> series + shares -> base metrics + elasticity + WACC -> snapshot dict.
        TargetMarkets: KR (semiconductor elasticity baselines); US needs US baselines.
    """
    series, shares, _currency = _getSeriesAndShares(company)
    base = _baseMetrics(series) if series else {"revenue": None, "margin": None, "netDebt": 0.0}

    sectorKey = _resolveSectorKey(company)
    elasticity = getElasticity(sectorKey) if sectorKey else DEFAULT_ELASTICITY

    sectorParams = None
    try:
        sectorParams = getattr(company, "sectorParams", None)
    except (AttributeError, ValueError):
        sectorParams = None
    baseWacc = getattr(sectorParams, "discountRate", None) or _DEFAULT_BASE_WACC
    terminalGrowth = min(getattr(sectorParams, "growthRate", None) or _TERMINAL_GROWTH_CAP, _TERMINAL_GROWTH_CAP)

    vintage = asOf or _latestPeriod(company) or "latest"

    return {
        "series": series,
        "baseRevenue": base["revenue"],
        "baseMargin": base["margin"],
        "netDebt": base["netDebt"] or 0.0,
        "shares": shares,
        "elasticity": elasticity,
        "sectorKey": sectorKey,
        "baseWacc": float(baseWacc),
        "terminalGrowth": float(terminalGrowth),
        "asOf": vintage,
        "latestAsOf": vintage,
    }


def _latestPeriod(company: Any) -> str | None:
    """Best-effort latest finance period label for the snapshot vintage (cached, single read).

    Reads the periods axis of the company's annual finance series (cached on the company, so this
    does not re-fetch). Returns the latest period (e.g. ``"2024"``) or None when unavailable; the
    caller then falls back to ``"latest"``.
    """
    try:
        ann = company._buildFinanceSeries(freq="Y")
    except (ValueError, KeyError, AttributeError):
        return None
    if not isinstance(ann, tuple) or len(ann) < 2:
        return None
    periods = ann[1]
    if isinstance(periods, (list, tuple)) and periods:
        return str(periods[0]) if str(periods[0]) >= str(periods[-1]) else str(periods[-1])
    return None


# ──────────────────────────────────────────────────────────────────────
# §5 deterministic node fns — each matches the evaluateSheet 7-tuple contract
# ──────────────────────────────────────────────────────────────────────


def _fnMacroPath(node: DriverNode, sheet: DriverSheet, depValues: dict):
    """`macro.path` node — preset GDP/rate/FX vector for the node's scenario (§5).

    Capabilities:
        Emits the preset macro path for the scenario named by ``node.scenarioId`` from
        `synth.scenario.getPresetScenarios` (KR), truncated to the snapshot horizon. The
        representative value is terminal-year GDP; the vector is the GDP path; the full
        rate / FX paths ride along in the frozen inputs for the downstream transfer node.

    Args:
        node: the macro.path DriverNode (its `scenarioId` selects the preset).
        sheet: the DriverSheet (its `snapshot["horizon"]` truncates the path).
        depValues: empty (macro.path is a root node).

    Returns:
        tuple: ``(gdpTerminal, gdpVector, provenance, refs, frozenInputs, asOf, latestAsOf)``
        with ``provenance = "preset:{scenarioId}"``.

    Raises:
        None — an unknown scenario id falls back to the baseline preset.

    Example:
        >>> # wired by buildScenarioSheet; not called directly.

    Requires:
        ``synth.scenario.getPresetScenarios`` and the snapshot's ``horizon`` / ``asOf``.
    """
    snap = sheet.snapshot
    horizon = snap["horizon"]
    presets = getPresetScenarios("KR")
    sc = presets.get(node.scenarioId) or presets["baseline"]
    gdp = list(sc.gdpGrowth[:horizon])
    rate = list(sc.interestRate[:horizon])
    fx = list(sc.krwUsd[:horizon])
    frozen = {"gdp": gdp, "rate": rate, "fx": fx}
    refs = (f"synth.scenario:PRESET_SCENARIOS_KR/{sc.name}",)
    value = gdp[-1] if gdp else None
    return value, tuple(gdp), f"preset:{node.scenarioId}", refs, frozen, snap["asOf"], snap["latestAsOf"]


def _fnRevPath(node: DriverNode, sheet: DriverSheet, depValues: dict):
    """`rev.path` node — the owned macro->fundamentals edge over the horizon (§2/§5).

    Capabilities:
        Chains `simulate.transfer.transferRevenuePath` over the macro paths (from the macro.path
        dep's frozen inputs) onto base revenue / margin + sector elasticity, producing the
        scenario's absolute revenue vector (with the margin / WACC paths carried in frozen inputs).
        This is the single piece of math the simulate engine owns. honest-gap: if base revenue is
        absent the node value is None (never 0).

    Args:
        node: the rev.path DriverNode (depends on the scenario's macro.path).
        sheet: the DriverSheet whose snapshot holds base revenue / margin / elasticity / WACC.
        depValues: ``{macroNodeId: NodeValue}`` — the macro.path output (GDP vector + frozen
            rate/FX paths).

    Returns:
        tuple: ``(revTerminal, revVector, provenance, refs, frozenInputs, asOf, latestAsOf)`` with
        ``provenance`` describing the transfer; value/vector are None when base revenue is absent.

    Raises:
        None.

    Example:
        >>> # wired by buildScenarioSheet; not called directly.

    Requires:
        The macro.path dep's frozen ``gdp``/``rate``/``fx`` and the snapshot base metrics.
    """
    from dartlab.simulate.transfer import transferRevenuePath

    snap = sheet.snapshot
    macroNv = next(iter(depValues.values()))
    macroFrozen = _macroFrozen(macroNv, snap["horizon"])
    baseRevenue = snap["baseRevenue"]
    if baseRevenue is None:
        # honest-gap: no base revenue -> no scenario path.
        frozen = {"gap": "baseRevenue_absent"}
        return None, None, "transfer:gap(baseRevenue_absent)", (), frozen, snap["asOf"], snap["latestAsOf"]

    baseMargin = snap["baseMargin"] if snap["baseMargin"] is not None else _DEFAULT_MARGIN
    elasticity: SectorElasticity = snap["elasticity"]
    revPath, marginPath, waccPath = transferRevenuePath(
        baseRevenue,
        baseMargin,
        macroFrozen["gdp"],
        macroFrozen["rate"],
        macroFrozen["fx"],
        elasticity,
        snap["baseWacc"],
    )
    frozen = {"rev": revPath, "margin": marginPath, "wacc": waccPath}
    prov = "transfer:rev*(1+bgdp*gdp+bfx*fxDelta),margin+bm*gdp,wacc+0.5*rateDelta"
    refs = ("simulate.transfer:transferRevenuePath",)
    value = revPath[-1] if revPath else None
    return value, tuple(revPath), prov, refs, frozen, snap["asOf"], snap["latestAsOf"]


def _fnProforma(node: DriverNode, sheet: DriverSheet, depValues: dict):
    """`proforma` node — call the L2 leaf buildProforma over the scenario growth path (§2/§5).

    Capabilities:
        Converts the rev.path absolute-revenue vector into the year-over-year growth path
        `buildProforma` expects (edge wiring owned by the node, not leaf math), then calls the L2
        leaf `analysis.financial.proforma.buildProforma` to produce IS/BS/CF projections. The
        node value is the terminal-year revenue; the vector is per-year FCF (so the dcf node can
        discount it). honest-gap: if rev.path produced no path the node is None / partial.

    Args:
        node: the proforma DriverNode (depends on rev.path).
        sheet: the DriverSheet whose snapshot holds the finance series + base revenue.
        depValues: ``{revNodeId: NodeValue}`` — the rev.path absolute revenue vector.

    Returns:
        tuple: ``(terminalRevenue, fcfVector, provenance, refs, frozenInputs, asOf, latestAsOf)``
        with ``provenance = "proforma:cashplug,wacc=..,years=.."``; value/vector None on gap.

    Raises:
        None — leaf failure is contained and reported as a gap value.

    Example:
        >>> # wired by buildScenarioSheet; not called directly.

    Requires:
        The L2 leaf ``buildProforma`` and the snapshot ``series`` / ``baseRevenue``.
    """
    snap = sheet.snapshot
    revNv = next(iter(depValues.values()))
    series = snap.get("series")
    base = snap["baseRevenue"]
    if revNv.vector is None or not revNv.vector or series is None or base is None:
        frozen = {"gap": "revPath_or_series_absent"}
        return None, None, "proforma:gap(revPath_or_series_absent)", (), frozen, snap["asOf"], snap["latestAsOf"]

    revPath = list(revNv.vector)
    growthPath: list[float] = []
    prev = base
    for r in revPath:
        growthPath.append((r / prev - 1.0) * 100.0 if prev else 0.0)
        prev = r

    pf = buildProforma(series, revenueGrowthPath=growthPath, scenarioName=node.scenarioId)
    proj = pf.projections
    if not proj:
        frozen = {"growthPath": [round(g, 9) for g in growthPath]}
        return None, None, "proforma:gap(no_projections)", (), frozen, snap["asOf"], snap["latestAsOf"]

    fcf = tuple(round(y.fcf, 2) for y in proj)
    frozen = {"growthPath": [round(g, 9) for g in growthPath], "wacc": round(pf.wacc, 9)}
    prov = f"proforma:cashplug,wacc={pf.wacc:.2f},years={len(proj)}"
    refs = ("analysis.financial.proforma:buildProforma",)
    return round(proj[-1].revenue, 2), fcf, prov, refs, frozen, snap["asOf"], snap["latestAsOf"]


def _fnDcf(node: DriverNode, sheet: DriverSheet, depValues: dict):
    """`dcf` node — FCFF discount off the proforma FCF path -> per-share value (§5).

    Capabilities:
        Discounts the proforma node's per-year FCF vector at the proforma WACC, adds a Gordon
        terminal value (capped at the sector terminal growth), nets out the snapshot net debt, and
        divides by shares for a per-share value. This is a faithful port of the legacy terminal-
        value formula, re-derived here so the value reflects THIS scenario's proforma FCF rather
        than re-running an independent model (see module docstring on why not `calcDFV`). honest-
        gap: a missing FCF path / shares yields a None per-share value with a partial-marking
        provenance.

    Args:
        node: the dcf DriverNode (depends on proforma).
        sheet: the DriverSheet whose snapshot holds netDebt / shares / WACC / terminalGrowth.
        depValues: ``{proformaNodeId: NodeValue}`` — the proforma FCF vector + WACC frozen input.

    Returns:
        tuple: ``(perShare, scalarVector, provenance, refs, frozenInputs, asOf, latestAsOf)``.
        ``scalarVector`` is a 1-tuple of enterprise value; ``perShare`` is None when FCF or shares
        are absent (honest-gap).

    Raises:
        None.

    Example:
        >>> # wired by buildScenarioSheet; not called directly.

    Requires:
        The proforma dep's FCF vector + frozen ``wacc`` and the snapshot ``netDebt`` / ``shares``.
    """
    snap = sheet.snapshot
    pfNv = next(iter(depValues.values()))
    if pfNv.vector is None or not pfNv.vector:
        frozen = {"gap": "fcfPath_absent"}
        return None, None, "dcf:gap(fcfPath_absent)", (), frozen, snap["asOf"], snap["latestAsOf"]

    fcfPath = [float(x) for x in pfNv.vector if x is not None]
    horizon = len(fcfPath)
    # WACC: snapshot base WACC (the leaf's per-run WACC is not surfaced on a NodeValue; the base
    # WACC is the deterministic, snapshot-frozen discount rate for the scenario).
    wacc = float(snap["baseWacc"])
    terminalGrowth = float(snap["terminalGrowth"])
    if wacc <= terminalGrowth:
        terminalGrowth = max(wacc - 2.0, 0.5)

    pvSum = sum(fcf / (1 + wacc / 100) ** (yr + 1) for yr, fcf in enumerate(fcfPath))
    terminalFcf = fcfPath[-1] if fcfPath else 0.0
    if terminalFcf > 0:
        tv = terminalFcf * (1 + terminalGrowth / 100) / (wacc / 100 - terminalGrowth / 100)
        pvTv = tv / (1 + wacc / 100) ** horizon
    else:
        pvTv = 0.0
    ev = pvSum + pvTv
    netDebt = snap["netDebt"] or 0.0
    equityValue = ev - netDebt
    shares = snap["shares"]
    perShare = (equityValue / shares) if shares and shares > 0 else None

    frozen = {
        "wacc": round(wacc, 9),
        "terminalGrowth": round(terminalGrowth, 9),
        "netDebt": round(netDebt, 2),
        "shares": shares,
    }
    gap = "" if perShare is not None else "(shares_absent)"
    prov = f"dcf:fcff,wacc={wacc:.2f},g={terminalGrowth:.2f}{gap}"
    refs = ("simulate.registry:fcffDiscount", "analysis.financial.proforma:buildProforma")
    return perShare, (round(ev, 2),), prov, refs, frozen, snap["asOf"], snap["latestAsOf"]


def _macroFrozen(macroNv, horizon: int) -> dict:
    """Recover the GDP/rate/FX paths the macro.path node carried (frozen inputs are not in NodeValue).

    The executor does not surface a node's frozen inputs on its `NodeValue`; the rev.path node
    only needs the rate/FX paths, which it re-derives from the same preset here, truncated to the
    horizon. The GDP vector is taken from the macro node's vector to keep it dep-driven.
    """
    presets = getPresetScenarios("KR")
    scenarioId = macroNv.provenance.split(":", 1)[1] if ":" in macroNv.provenance else "baseline"
    sc = presets.get(scenarioId) or presets["baseline"]
    gdp = list(macroNv.vector) if macroNv.vector else list(sc.gdpGrowth[:horizon])
    return {"gdp": gdp, "rate": list(sc.interestRate[:horizon]), "fx": list(sc.krwUsd[:horizon])}


# ──────────────────────────────────────────────────────────────────────
# sheet builder
# ──────────────────────────────────────────────────────────────────────


def buildScenarioSheet(snapshot: dict, *, scenario: str, horizon: int) -> DriverSheet:
    """Wire the deterministic 4-node DriverSheet for one scenario over a frozen snapshot (§5/§6).

    Capabilities:
        Builds the ``macro.path -> rev.path -> proforma -> dcf`` chain for a single scenario,
        registering each driver fn and adding the nodes with the §6.1 3-coordinate
        ``{driverId}@{scenarioId}#{periodKey}`` ids. The returned sheet is ready for
        `evaluateSheet`; the snapshot (read once by `buildSnapshot`) is attached with the scenario
        horizon so every node reads from it without reloading data.

    Args:
        snapshot: the frozen base-metric snapshot from `buildSnapshot`.
        scenario: the scenario id (e.g. ``"baseline"`` / ``"adverse"``) — selects the macro preset
            and stamps every node's `scenarioId`.
        horizon: number of forecast years (paths are truncated to this length).

    Returns:
        DriverSheet: a wired sheet with 4 nodes and the deterministic registry. Pass to
        `evaluateSheet` to fill each node's `det`.

    Raises:
        None — wiring validity (cycle / missing dep) is enforced later by `buildOrder` inside
        `evaluateSheet`.

    Example:
        >>> snap = buildSnapshot(Company("005930"))  # doctest: +SKIP
        >>> sheet = buildScenarioSheet(snap, scenario="baseline", horizon=3)  # doctest: +SKIP
        >>> len(sheet.nodes)  # doctest: +SKIP
        4

    Guide:
        Build one sheet per scenario over a shared snapshot; baseline vs adverse differ only in
        the macro preset (the elasticity / base metrics are identical), which is exactly the
        scenario-comparison contract.

    SeeAlso:
        - ``buildSnapshot``: produces the snapshot this consumes.
        - ``dartlab.simulate.sheet.evaluateSheet``: evaluates the wired sheet.
        - ``dartlab.simulate.run.runScenario``: the end-to-end driver.

    Requires:
        A snapshot dict from `buildSnapshot` (so the nodes have base metrics + asOf).

    AIContext:
        The sheet is the audit object — each node's `det.provenance`/`refs` tells the user which
        L2 leaf produced it; never blend a (future) lens opinion into `det`.

    LLM Specifications:
        AntiPatterns:
            - Reusing one sheet across scenarios — each scenario gets its own macro preset / ids.
            - Mutating the snapshot per node — breaks re-run determinism.
        OutputSchema: ``DriverSheet`` with 4 nodes + a 4-entry registry.
        Prerequisites: a `buildSnapshot` result.
        Freshness: inherits the snapshot's `asOf`/`latestAsOf`.
        Dataflow: snapshot+scenario -> register fns -> add macro/rev/proforma/dcf nodes -> sheet.
        TargetMarkets: KR presets (getPresetScenarios("KR")); US needs US presets.
    """
    snap = dict(snapshot)
    snap["horizon"] = horizon
    sheet = DriverSheet(snapshot=snap)
    sheet.registry[_FN_MACRO] = _fnMacroPath
    sheet.registry[_FN_REV] = _fnRevPath
    sheet.registry[_FN_PROFORMA] = _fnProforma
    sheet.registry[_FN_DCF] = _fnDcf

    macroId = f"{DRIVER_MACRO}@{scenario}#all"
    revId = f"{DRIVER_REV}@{scenario}#all"
    proformaId = f"{DRIVER_PROFORMA}@{scenario}#all"
    dcfId = f"{DRIVER_DCF}@{scenario}#all"

    sheet.add(DriverNode(macroId, DRIVER_MACRO, scenario, "all", (), _FN_MACRO))
    sheet.add(DriverNode(revId, DRIVER_REV, scenario, "all", (macroId,), _FN_REV))
    sheet.add(DriverNode(proformaId, DRIVER_PROFORMA, scenario, "all", (revId,), _FN_PROFORMA))
    sheet.add(DriverNode(dcfId, DRIVER_DCF, scenario, "all", (proformaId,), _FN_DCF))
    return sheet
