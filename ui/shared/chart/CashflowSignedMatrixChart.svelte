<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="cashflow-signed-matrix") 렌더러.
   *
   * spec.series = [{name, data: [...], color, signed, tone, unit}]
   * spec.categories = periods
   * spec.options.latest = [{id, label, value, unit, tone}, ...]
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  const W = 720;
  const H = 240;
  const M = { top: 18, right: 18, bottom: 28, left: 56 };
  const plotW = W - M.left - M.right;
  const plotH = H - M.top - M.bottom;

  function isFinite(v) { return typeof v === 'number' && Number.isFinite(v); }
  function periods() { return spec?.categories ?? []; }
  function series() { return spec?.series ?? []; }
  function latest() { return spec?.options?.latest ?? []; }

  function extent() {
    const vals = series().flatMap((s) => (s.data ?? []).filter(isFinite));
    if (!vals.length) return [-1, 1];
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

  function barAttrs(s, sIdx, sCount, i, ext) {
    const v = s.data?.[i];
    if (!isFinite(v)) return null;
    const n = periods().length;
    const slotW = plotW / Math.max(n, 1);
    const groupW = slotW * 0.72;
    const barW = groupW / Math.max(sCount, 1);
    const cx = M.left + (i + 0.5) * slotW - groupW / 2 + sIdx * barW;
    const yTop = y(Math.max(v, 0), ext);
    const yBot = y(Math.min(v, 0), ext);
    return { x: cx, y: yTop, w: barW * 0.92, h: Math.max(1, yBot - yTop) };
  }

  function handleClick(s, i) {
    if (typeof onPointClick !== 'function') return;
    const v = s.data?.[i];
    if (!isFinite(v)) return;
    onPointClick({
      period: periods()[i],
      value: v,
      name: s.name,
      pointRef: (s.pointRefs ?? [])[i] ?? null
    });
  }

  function fmt(v) {
    if (v == null || !Number.isFinite(v)) return '—';
    return v.toFixed(1);
  }
</script>

{#if series().length && periods().length}
  {@const ext = extent()}
  {@const zeroY = y(0, ext)}
  <figure class="cashflow-signed">
    {#if spec.title}<figcaption>{spec.title}</figcaption>{/if}
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={spec.title}>
      <line x1={M.left} y1={zeroY} x2={M.left + plotW} y2={zeroY} stroke="#475569" stroke-width="1" />
      {#each series() as s, sIdx}
        {#each (s.data ?? []) as v, i}
          {@const a = barAttrs(s, sIdx, series().length, i, ext)}
          {#if a}
            <rect
              x={a.x} y={a.y} width={a.w} height={a.h}
              fill={v >= 0 ? (s.color || '#34d399') : '#ef4444'}
              fill-opacity="0.85"
              onclick={() => handleClick(s, i)}
            />
          {/if}
        {/each}
      {/each}
      {#each periods() as p, i}
        <text x={M.left + (i + 0.5) * (plotW / Math.max(periods().length, 1))} y={H - 8}
          fill="#64748b" font-size="10" text-anchor="middle">{p}</text>
      {/each}
    </svg>
    <ul class="legend">
      {#each series() as s}
        <li>
          <i style={`background: ${s.color || '#34d399'};`}></i>
          {s.name}{#if s.unit}<small>({s.unit})</small>{/if}
        </li>
      {/each}
    </ul>
    {#if latest().length}
      <ul class="latest">
        {#each latest() as p}
          <li class={p.tone || ''}>
            <span>{p.label}</span>
            <strong>{fmt(p.value)}<small>{p.unit || ''}</small></strong>
          </li>
        {/each}
      </ul>
    {/if}
  </figure>
{/if}

<style>
  .cashflow-signed {
    margin: 0;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: rgba(8, 13, 23, 0.96);
    padding: 11px 14px;
    color: #cbd5e1;
  }
  figcaption {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  svg { width: 100%; height: auto; }
  rect { cursor: pointer; }
  rect:hover { fill-opacity: 1; }
  .legend, .latest {
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
  .latest { margin-top: 8px; }
  .latest li {
    border: 1px solid #263145;
    border-radius: 5px;
    padding: 5px 8px;
    background: #070c15;
  }
  .latest li span { color: #94a3b8; margin-right: 6px; }
  .latest li strong { color: #f1f5f9; }
  .latest li.good strong { color: #34d399; }
  .latest li.bad strong { color: #f87171; }
  .latest li.watch strong { color: #fbbf24; }
</style>
