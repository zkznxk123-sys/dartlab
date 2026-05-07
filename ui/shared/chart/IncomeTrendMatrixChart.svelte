<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="income-trend-matrix") 렌더러.
   *
   * spec.series = [{name: "매출액"|"영업이익"|"당기순이익"|"영업이익률"|"순이익률",
   *                  data: [...], color, type, axis: "amount"|"margin", unit}]
   * spec.categories = periods
   * spec.options.secondaryY = ["영업이익률", "순이익률"] (% axis)
   *
   * 데이터포인트 클릭시 onPointClick({period, value, name, ...}).
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  const W = 760;
  const H = 280;
  const M = { top: 18, right: 56, bottom: 28, left: 56 };
  const plotW = W - M.left - M.right;
  const plotH = H - M.top - M.bottom;

  function isFinite(v) {
    return typeof v === 'number' && Number.isFinite(v);
  }

  function categories() { return spec?.categories ?? []; }
  function series() { return spec?.series ?? []; }
  function isMargin(s) { return s.axis === 'margin'; }

  function amountSeries() { return series().filter((s) => !isMargin(s)); }
  function marginSeries() { return series().filter(isMargin); }

  function extentOf(slist) {
    const vals = slist.flatMap((s) => (s.data ?? []).filter(isFinite));
    if (!vals.length) return [0, 1];
    const min = Math.min(0, ...vals);
    const max = Math.max(0, ...vals);
    const pad = (max - min || Math.max(Math.abs(max), 1)) * 0.12;
    return [min - pad, max + pad];
  }

  function x(i, n) {
    if (n <= 1) return M.left + plotW / 2;
    return M.left + (i / (n - 1)) * plotW;
  }
  function y(v, [min, max]) {
    return M.top + plotH - ((v - min) / (max - min || 1)) * plotH;
  }

  function path(s, ext) {
    const cats = categories();
    return (s.data ?? [])
      .map((v, i) => {
        if (!isFinite(v)) return '';
        const cmd = i === 0 || !isFinite(s.data[i - 1]) ? 'M' : 'L';
        return `${cmd}${x(i, cats.length).toFixed(1)},${y(v, ext).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(' ');
  }

  function barAttrs(s, ext, i, n) {
    const v = s.data?.[i];
    if (!isFinite(v)) return null;
    const cx = x(i, n);
    const w = Math.max(8, plotW / Math.max(n, 1) * 0.55);
    const yTop = y(Math.max(v, 0), ext);
    const yBot = y(Math.min(v, 0), ext);
    return { x: cx - w / 2, y: yTop, w, h: Math.max(1, yBot - yTop) };
  }

  function handlePoint(s, i, v) {
    if (typeof onPointClick !== 'function' || !isFinite(v)) return;
    onPointClick({
      period: categories()[i],
      value: v,
      name: s.name,
      pointRef: (s.pointRefs ?? [])[i] ?? null
    });
  }
</script>

{#if series().length && categories().length}
  {@const amtExt = extentOf(amountSeries())}
  {@const mrgExt = extentOf(marginSeries())}
  <figure class="income-trend">
    {#if spec.title}<figcaption>{spec.title}</figcaption>{/if}
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={spec.title}>
      {#each amountSeries() as s}
        {#if s.type === 'bar'}
          {#each (s.data ?? []) as v, i}
            {@const a = barAttrs(s, amtExt, i, categories().length)}
            {#if a}
              <rect
                x={a.x} y={a.y} width={a.w} height={a.h}
                fill={s.color || '#60a5fa'} fill-opacity="0.85"
                onclick={() => handlePoint(s, i, v)}
              />
            {/if}
          {/each}
        {:else}
          <path d={path(s, amtExt)} stroke={s.color || '#60a5fa'} stroke-width="2" fill="none" />
          {#each (s.data ?? []) as v, i}
            {#if isFinite(v)}
              <circle cx={x(i, categories().length)} cy={y(v, amtExt)} r="3"
                fill={s.color || '#60a5fa'}
                onclick={() => handlePoint(s, i, v)}
              />
            {/if}
          {/each}
        {/if}
      {/each}
      {#each marginSeries() as s}
        <path d={path(s, mrgExt)} stroke={s.color || '#fb923c'} stroke-width="1.4"
          stroke-dasharray="3 3" fill="none" />
        {#each (s.data ?? []) as v, i}
          {#if isFinite(v)}
            <circle cx={x(i, categories().length)} cy={y(v, mrgExt)} r="2.5"
              fill={s.color || '#fb923c'}
              onclick={() => handlePoint(s, i, v)}
            />
          {/if}
        {/each}
      {/each}
      {#each categories() as cat, i}
        <text x={x(i, categories().length)} y={H - 8} fill="#64748b" font-size="10"
          text-anchor="middle">{cat}</text>
      {/each}
    </svg>
    <ul class="legend">
      {#each series() as s}
        <li>
          <i style={`background: ${s.color || '#60a5fa'};`}></i>
          {s.name}{#if s.unit}<small>({s.unit})</small>{/if}
        </li>
      {/each}
    </ul>
  </figure>
{/if}

<style>
  .income-trend {
    margin: 0;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: rgba(8, 13, 23, 0.96);
    padding: 11px 14px;
  }
  figcaption {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  svg { width: 100%; height: auto; }
  .legend {
    list-style: none;
    margin: 6px 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 11px;
    color: #94a3b8;
  }
  .legend li { display: flex; align-items: center; gap: 5px; }
  .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; }
  .legend small { color: #64748b; font-size: 10px; }
  rect, circle { cursor: pointer; }
  rect:hover, circle:hover { fill-opacity: 1; r: 4; }
</style>
