<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="price-chart") 렌더러.
   *
   * spec.data = [{date, open, high, low, close, volume, ma20?, ma60?}]
   * spec.options.benchmarkSeries = [{date, value}]  # 100 기준 상대지수
   * spec.options.events = [{date, label, tone}]
   */
  import { scaleBand, scaleLinear } from 'd3-scale';
  import { COLORS } from './colors.js';

  let { spec, onPointClick } = $props();

  let containerEl = $state(null);
  let containerWidth = $state(640);
  let hoverIndex = $state(-1);
  let range = $state('1Y');
  let mode = $state('candlestick');

  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver(([entry]) => {
      containerWidth = Math.max(320, entry.contentRect.width);
    });
    ro.observe(containerEl);
    return () => ro.disconnect();
  });

  const HEIGHT = 360;
  const PRICE_H = 220;
  const VOL_H = 58;
  const GAP = 18;
  const MARGIN = { top: 34, right: 48, bottom: 34, left: 58 };

  let plotW = $derived(Math.max(120, containerWidth - MARGIN.left - MARGIN.right));
  let rows = $derived.by(() => normalizeRows(spec?.data || []));
  let visibleRows = $derived.by(() => sliceRange(rows, range));
  let dates = $derived(visibleRows.map((row) => row.date));
  let overlays = $derived(spec?.options?.overlays || []);
  let benchmarkRows = $derived.by(() => normalizeBenchmark(spec?.options?.benchmarkSeries || [], dates));
  let events = $derived(spec?.options?.events || []);

  let priceValues = $derived.by(() => {
    const vals = [];
    for (const row of visibleRows) {
      for (const key of ['open', 'high', 'low', 'close', ...overlays]) {
        if (Number.isFinite(row[key])) vals.push(row[key]);
      }
    }
    return vals;
  });
  let volumeValues = $derived(visibleRows.map((row) => row.volume).filter((value) => Number.isFinite(value)));
  let benchValues = $derived(benchmarkRows.map((row) => row.value).filter((value) => Number.isFinite(value)));

  let priceMin = $derived(Math.min(...priceValues));
  let priceMax = $derived(Math.max(...priceValues));
  let pricePad = $derived((priceMax - priceMin) * 0.08 || priceMax * 0.02 || 1);
  let xScale = $derived(scaleBand().domain(dates).range([0, plotW]).padding(0.22));
  let yPrice = $derived(scaleLinear().domain([priceMin - pricePad, priceMax + pricePad]).range([PRICE_H, 0]).nice());
  let yVolume = $derived(scaleLinear().domain([0, Math.max(...volumeValues, 1)]).range([VOL_H, 0]).nice());
  let yBench = $derived.by(() => {
    const min = Math.min(...benchValues, 96);
    const max = Math.max(...benchValues, 104);
    const pad = (max - min) * 0.1 || 1;
    return scaleLinear().domain([min - pad, max + pad]).range([PRICE_H, 0]).nice();
  });

  let yTicks = $derived(yPrice.ticks(5));
  let rangeOptions = [
    ['3M', '3M'],
    ['6M', '6M'],
    ['1Y', '1Y'],
    ['ALL', 'All']
  ];
  let hasCandles = $derived(visibleRows.some((row) => Number.isFinite(row.open) && Number.isFinite(row.high) && Number.isFinite(row.low)));
  let activeMode = $derived(mode === 'candlestick' && hasCandles ? 'candlestick' : 'line');
  let latest = $derived(visibleRows[visibleRows.length - 1]);
  let first = $derived(visibleRows[0]);
  let returnPct = $derived(first?.close ? ((latest?.close - first.close) / first.close) * 100 : null);

  function normalizeRows(items) {
    return (items || [])
      .map((row) => ({
        ...row,
        date: String(row.date ?? row.BAS_DD ?? ''),
        open: toNumber(row.open),
        high: toNumber(row.high),
        low: toNumber(row.low),
        close: toNumber(row.close),
        volume: toNumber(row.volume),
        ma20: toNumber(row.ma20),
        ma60: toNumber(row.ma60),
        ma120: toNumber(row.ma120)
      }))
      .filter((row) => row.date && Number.isFinite(row.close))
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  function normalizeBenchmark(items, visibleDates) {
    const byDate = new Map((items || []).map((row) => [String(row.date), toNumber(row.value)]));
    return visibleDates.map((date) => ({ date, value: byDate.get(date) }));
  }

  function sliceRange(items, selected) {
    const limit = selected === '3M' ? 66 : selected === '6M' ? 132 : selected === '1Y' ? 252 : items.length;
    return items.slice(Math.max(0, items.length - limit));
  }

  function toNumber(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value !== 'string') return null;
    const normalized = value.replace(/,/g, '').trim();
    if (!normalized) return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatNum(value) {
    if (!Number.isFinite(value)) return '-';
    if (Math.abs(value) >= 1e12) return `${(value / 1e12).toFixed(1)}조`;
    if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(1)}억`;
    if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(0)}만`;
    if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function xMid(date) {
    return (xScale(date) ?? 0) + xScale.bandwidth() / 2;
  }

  function linePath(key, yScale = yPrice) {
    return visibleRows
      .map((row, i) => {
        const value = row[key];
        if (!Number.isFinite(value)) return null;
        return `${i === 0 ? 'M' : 'L'}${xMid(row.date)},${yScale(value)}`;
      })
      .filter(Boolean)
      .join(' ');
  }

  function benchmarkPath() {
    return benchmarkRows
      .map((row, i) => {
        if (!Number.isFinite(row.value)) return null;
        return `${i === 0 ? 'M' : 'L'}${xMid(row.date)},${yBench(row.value)}`;
      })
      .filter(Boolean)
      .join(' ');
  }

  function labelEvery(i) {
    return i === 0 || i === dates.length - 1 || i % Math.max(1, Math.ceil(dates.length / 6)) === 0;
  }

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left - MARGIN.left;
    let best = -1;
    let bestDist = Infinity;
    for (let i = 0; i < dates.length; i += 1) {
      const dist = Math.abs(xMid(dates[i]) - x);
      if (dist < bestDist) {
        bestDist = dist;
        best = i;
      }
    }
    hoverIndex = best;
  }

  function onLeave() {
    hoverIndex = -1;
  }

  function handleClick(row) {
    if (typeof onPointClick !== 'function') return;
    onPointClick({
      period: row.date,
      name: 'close',
      value: row.close,
      pointRef: {
        period: row.date,
        valueRef: `gather:${spec?.meta?.stockCode || ''}:price:close:${row.date}`
      }
    });
  }

  function handleKey(e, row) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    e.preventDefault();
    handleClick(row);
  }

  function eventForDate(date) {
    return events.find((item) => String(item.date) === date);
  }
</script>

{#if visibleRows.length >= 2}
  <figure class="price-chart" bind:this={containerEl}>
    {#if spec?.title}<figcaption>{spec.title}</figcaption>{/if}
    <header class="chart-head">
      <div>
        <p>{latest?.date} · {formatNum(latest?.close)}{spec?.options?.unit ? ` ${spec.options.unit}` : ''}</p>
      </div>
      <div class="head-metrics">
        <span class:good={returnPct > 0} class:bad={returnPct < 0}>{returnPct == null ? '-' : `${returnPct.toFixed(1)}%`}</span>
      </div>
    </header>

    <div class="controls" aria-label="주가차트 옵션">
      <div class="seg">
        {#each rangeOptions as option}
          <button type="button" class:active={range === option[0]} onclick={() => (range = option[0])}>{option[1]}</button>
        {/each}
      </div>
      <div class="seg">
        <button type="button" class:active={activeMode === 'candlestick'} disabled={!hasCandles} onclick={() => (mode = 'candlestick')}>Candle</button>
        <button type="button" class:active={activeMode === 'line'} onclick={() => (mode = 'line')}>Line</button>
      </div>
    </div>

    <svg
      viewBox="0 0 {containerWidth} {HEIGHT}"
      class="chart-svg"
      onpointermove={onMove}
      onpointerleave={onLeave}
      role="img"
      aria-label={spec?.title || '주가차트'}
    >
      <g transform="translate({MARGIN.left},{MARGIN.top})">
        {#each yTicks as tick}
          <line x1="0" y1={yPrice(tick)} x2={plotW} y2={yPrice(tick)} class="grid" />
          <text x="-8" y={yPrice(tick)} dy="0.35em" text-anchor="end" class="axis-label">{formatNum(tick)}</text>
        {/each}

        {#if benchmarkRows.some((row) => Number.isFinite(row.value))}
          <path d={benchmarkPath()} class="benchmark-line" />
          <text x={plotW + 8} y={12} class="bench-label">{spec?.options?.benchmarkName || 'BM'} 100</text>
        {/if}

        {#if activeMode === 'line'}
          <path d={linePath('close')} class="close-line" />
        {:else}
          {#each visibleRows as row}
            {@const up = row.close >= row.open}
            {@const bodyY = yPrice(Math.max(row.open ?? row.close, row.close))}
            {@const bodyH = Math.max(1, Math.abs(yPrice(row.open ?? row.close) - yPrice(row.close)))}
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <g
              class:up
              class:down={!up}
              class="candle"
              onclick={() => handleClick(row)}
              onkeydown={(e) => handleKey(e, row)}
              role={typeof onPointClick === 'function' ? 'button' : undefined}
              tabindex={typeof onPointClick === 'function' ? 0 : undefined}
            >
              <line x1={xMid(row.date)} x2={xMid(row.date)} y1={yPrice(row.high ?? row.close)} y2={yPrice(row.low ?? row.close)} />
              <rect x={(xScale(row.date) ?? 0)} y={bodyY} width={Math.max(2, xScale.bandwidth())} height={bodyH} rx="1.5" />
            </g>
          {/each}
        {/if}

        {#each overlays as key, i}
          {#if visibleRows.some((row) => Number.isFinite(row[key]))}
            <path d={linePath(key)} class="ma-line" style={`stroke: ${COLORS[(i + 4) % COLORS.length]};`} />
          {/if}
        {/each}

        {#each visibleRows as row, i}
          {@const ev = eventForDate(row.date)}
          {#if ev}
            <g transform="translate({xMid(row.date)},{-8})" class="event-marker">
              <path d="M0,0 L5,9 L-5,9 Z" />
              <title>{ev.label || row.date}</title>
            </g>
          {/if}
        {/each}

        {#if hoverIndex >= 0}
          {@const row = visibleRows[hoverIndex]}
          <line x1={xMid(row.date)} x2={xMid(row.date)} y1="0" y2={PRICE_H + GAP + VOL_H} class="crosshair" />
          <circle cx={xMid(row.date)} cy={yPrice(row.close)} r="4" class="hover-dot" />
        {/if}

        <g transform="translate(0,{PRICE_H + GAP})">
          {#each visibleRows as row}
            {@const up = row.close >= row.open}
            <rect
              x={(xScale(row.date) ?? 0)}
              y={yVolume(row.volume || 0)}
              width={Math.max(1, xScale.bandwidth())}
              height={VOL_H - yVolume(row.volume || 0)}
              class:vol-up={up}
              class:vol-down={!up}
              rx="1"
            />
          {/each}
          <line x1="0" y1={VOL_H} x2={plotW} y2={VOL_H} class="axis-line" />
        </g>

        {#each dates as date, i}
          {#if labelEvery(i)}
            <text x={xMid(date)} y={PRICE_H + GAP + VOL_H + 22} text-anchor="middle" class="x-label">{date}</text>
          {/if}
        {/each}
      </g>
    </svg>

    {#if hoverIndex >= 0}
      {@const row = visibleRows[hoverIndex]}
      <div class="tooltip">
        <b>{row.date}</b>
        <span>O {formatNum(row.open)} · H {formatNum(row.high)} · L {formatNum(row.low)} · C {formatNum(row.close)}</span>
        <span>거래량 {formatNum(row.volume)}</span>
      </div>
    {/if}

    <footer class="legend">
      <span><i class="close"></i>종가</span>
      {#each overlays as key, i}
        <span><i style={`background: ${COLORS[(i + 4) % COLORS.length]};`}></i>{key.toUpperCase()}</span>
      {/each}
      {#if spec?.options?.benchmarkName}<span><i class="bench"></i>{spec.options.benchmarkName}</span>{/if}
    </footer>
  </figure>
{/if}

<style>
  .price-chart {
    margin: 0;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: rgba(8, 13, 23, 0.97);
    padding: 12px 14px 10px;
    color: #cbd5e1;
  }
  .chart-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }
  figcaption {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 3px;
  }
  .chart-head p {
    margin: 0;
    color: #94a3b8;
    font-size: 11px;
  }
  .head-metrics span {
    font: 700 16px/1 var(--dl-font-mono, ui-monospace, monospace);
    color: #cbd5e1;
  }
  .head-metrics span.good { color: #34d399; }
  .head-metrics span.bad { color: #f87171; }
  .controls {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
    flex-wrap: wrap;
  }
  .seg {
    display: inline-flex;
    border: 1px solid #263145;
    border-radius: 6px;
    overflow: hidden;
    background: #070c15;
  }
  .seg button {
    min-width: 42px;
    padding: 4px 8px;
    border: 0;
    border-right: 1px solid #263145;
    background: transparent;
    color: #94a3b8;
    font-size: 10px;
    cursor: pointer;
  }
  .seg button:last-child { border-right: 0; }
  .seg button.active {
    background: #1f2937;
    color: #f8fafc;
  }
  .seg button:disabled {
    color: #475569;
    cursor: not-allowed;
  }
  .chart-svg {
    width: 100%;
    height: auto;
    display: block;
    user-select: none;
  }
  .grid {
    stroke: #202939;
    stroke-width: 1;
  }
  .axis-line {
    stroke: #334155;
    stroke-width: 1;
  }
  .axis-label,
  .x-label,
  .bench-label {
    fill: #64748b;
    font-size: 10px;
  }
  .close-line {
    fill: none;
    stroke: #60a5fa;
    stroke-width: 2;
  }
  .ma-line {
    fill: none;
    stroke-width: 1.4;
    opacity: 0.9;
  }
  .benchmark-line {
    fill: none;
    stroke: #a78bfa;
    stroke-width: 1.5;
    stroke-dasharray: 4 4;
    opacity: 0.9;
  }
  .candle {
    cursor: pointer;
  }
  .candle line {
    stroke-width: 1.2;
  }
  .candle rect {
    opacity: 0.9;
  }
  .candle.up line,
  .candle.up rect {
    stroke: #34d399;
    fill: #34d399;
  }
  .candle.down line,
  .candle.down rect {
    stroke: #f87171;
    fill: #f87171;
  }
  .vol-up {
    fill: rgba(52, 211, 153, 0.34);
  }
  .vol-down {
    fill: rgba(248, 113, 113, 0.34);
  }
  .crosshair {
    stroke: #94a3b8;
    stroke-width: 1;
    stroke-dasharray: 3 3;
    opacity: 0.55;
  }
  .hover-dot {
    fill: #f8fafc;
    stroke: #60a5fa;
    stroke-width: 2;
  }
  .event-marker path {
    fill: #f59e0b;
  }
  .tooltip {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 6px;
    padding: 6px 8px;
    border: 1px solid #263145;
    border-radius: 5px;
    background: #070c15;
    color: #94a3b8;
    font-size: 11px;
  }
  .tooltip b {
    color: #f8fafc;
  }
  .legend {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 7px;
    color: #94a3b8;
    font-size: 10px;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .legend i {
    width: 12px;
    height: 3px;
    border-radius: 999px;
    background: #60a5fa;
  }
  .legend i.bench {
    background: repeating-linear-gradient(90deg, #a78bfa 0 4px, transparent 4px 7px);
  }
</style>
