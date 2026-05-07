<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="kpi-ribbon") 렌더러.
   *
   * spec.series[i].kpi = {id, label, value, unit, period, delta, deltaTone, tone, note, valueRef}
   * spec.series[i].data = sparkline 막대 값 배열.
   *
   * 카드 클릭시 onPointClick({valueRef, label, ...kpi}) 호출 — EvidencePanel 진입점.
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  function barStyle(values, value) {
    const nums = (values || []).filter((v) => v != null && Number.isFinite(v));
    if (!nums.length || value == null || !Number.isFinite(value)) {
      return 'height: 2px; opacity: 0.18; background: #64748b;';
    }
    const min = Math.min(0, ...nums);
    const max = Math.max(...nums);
    const span = max - min || 1;
    const height = Math.max(3, ((value - min) / span) * 28 + 3);
    const color = value < 0 ? '#ef4444' : '#fb923c';
    return `height: ${height.toFixed(1)}px; background: ${color};`;
  }

  function handleClick(serie) {
    const kpi = serie.kpi || {};
    if (typeof onPointClick === 'function') {
      onPointClick({
        valueRef: kpi.valueRef,
        label: kpi.label,
        period: kpi.period,
        kpi
      });
    }
  }
</script>

{#if spec?.series?.length}
  <section class="kpi-ribbon" aria-label={spec.title || '핵심 지표'}>
    {#each spec.series as serie}
      {@const kpi = serie.kpi || {}}
      <article
        class="kpi {kpi.tone || ''}"
        class:clickable={typeof onPointClick === 'function' && kpi.valueRef}
        role={typeof onPointClick === 'function' && kpi.valueRef ? 'button' : undefined}
        tabindex={typeof onPointClick === 'function' && kpi.valueRef ? 0 : undefined}
        onclick={() => handleClick(serie)}
        onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(serie)}
      >
        <div class="top">
          <span>{kpi.label || ''}</span>
          {#if kpi.note}<em>{kpi.note}</em>{/if}
        </div>
        <strong>{kpi.value ?? '—'}</strong>
        <div class="bottom">
          <small class={kpi.deltaTone || ''}>{kpi.delta || kpi.period || '비교 대기'}</small>
          {#if kpi.unit}<small class="unit">{kpi.unit}</small>{/if}
        </div>
        {#if (serie.data || []).length}
          <div class="spark" aria-hidden="true">
            {#each serie.data as value}
              <i class:negative={(value ?? 0) < 0} style={barStyle(serie.data, value)}></i>
            {/each}
          </div>
        {/if}
      </article>
    {/each}
  </section>
{/if}

<style>
  .kpi-ribbon {
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 8px;
    width: 100%;
  }
  .kpi {
    min-width: 0;
    height: 132px;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: linear-gradient(180deg, #08101c 0%, #060b13 100%);
    padding: 11px;
    color: #f8fafc;
    text-align: left;
    display: flex;
    flex-direction: column;
  }
  .kpi.clickable {
    cursor: pointer;
    transition: border-color 0.15s ease, transform 0.15s ease;
  }
  .kpi.clickable:hover {
    border-color: #fb923c;
    transform: translateY(-1px);
  }
  .top, .bottom {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: center;
  }
  span, small, em {
    color: #94a3b8;
    font-size: 11px;
    font-style: normal;
  }
  em {
    color: #fbbf24;
  }
  strong {
    display: block;
    margin-top: 8px;
    min-height: 42px;
    font-size: clamp(16px, 1vw, 20px);
    font-weight: 820;
    line-height: 1.08;
    overflow-wrap: anywhere;
  }
  small.good { color: #34d399; }
  .bad strong, small.bad { color: #f87171; }
  .watch strong { color: #fbbf24; }
  small.watch { color: #fbbf24; }
  .missing strong { color: #64748b; }
  small.unit { font-size: 10px; opacity: 0.7; }
  .spark {
    display: flex;
    align-items: end;
    gap: 3px;
    height: 28px;
    margin-top: 6px;
  }
  .spark i {
    display: block;
    flex: 1 1 0;
    min-width: 3px;
    border-radius: 2px 2px 0 0;
    background: #fb923c;
  }
  .spark i.negative { background: #ea4647; }
  @media (max-width: 1260px) {
    .kpi-ribbon { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  }
  @media (max-width: 700px) {
    .kpi-ribbon {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      overscroll-behavior-x: contain;
      scroll-snap-type: x proximity;
    }
    .kpi {
      flex: 0 0 142px;
      height: 112px;
      padding: 9px;
      scroll-snap-align: start;
    }
  }
</style>
