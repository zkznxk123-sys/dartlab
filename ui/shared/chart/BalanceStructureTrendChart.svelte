<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="balance-structure-trend") 렌더러.
   *
   * spec.series = [{name: "자산::유동자산"|"조달::부채"|...,
   *                  data: [...], shares: [...], color, stack, tone, unit, missing}]
   * spec.categories = periods
   * spec.options.totalAssetsSeries = [...] (top metric)
   * spec.options.debtRatio = number
   * spec.options.assetDeltaParts = [...]
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  function periods() { return spec?.categories ?? []; }
  function series() { return spec?.series ?? []; }
  function totalAssets() { return spec?.options?.totalAssetsSeries ?? []; }
  function totalFunding() { return spec?.options?.totalFundingSeries ?? []; }
  function debtRatio() { return spec?.options?.debtRatio; }
  function deltaParts() { return spec?.options?.assetDeltaParts ?? []; }

  function group(g) {
    return series().filter((s) => (s.name || '').startsWith(`${g}::`));
  }

  function shareOf(s, i) {
    const v = s.shares?.[i];
    return Number.isFinite(v) ? Math.max(0, Math.min(100, v)) : 0;
  }

  function handleClick(s, i) {
    if (typeof onPointClick !== 'function') return;
    onPointClick({
      period: periods()[i],
      name: s.name,
      value: s.data?.[i],
      share: s.shares?.[i],
      pointRef: (s.pointRefs ?? [])[i] ?? null
    });
  }

  function fmt(v) {
    if (v == null || !Number.isFinite(v)) return '—';
    return v.toFixed(1);
  }
</script>

{#if series().length && periods().length}
  <figure class="balance-structure">
    {#if spec.title}<figcaption>{spec.title}</figcaption>{/if}
    {#if debtRatio() != null}
      <div class="head-stat">
        <span>부채비율</span>
        <strong>{fmt(debtRatio())}<small>%</small></strong>
      </div>
    {/if}
    <div class="bands">
      {#each ['자산', '조달', '자본'] as gname}
        {@const gs = group(gname)}
        {#if gs.length}
          <section>
            <h4>{gname}</h4>
            <div class="period-grid" style={`grid-template-columns: repeat(${periods().length}, minmax(0, 1fr));`}>
              {#each periods() as p, i}
                <div class="period">
                  <div class="stack">
                    {#each gs as s}
                      <i
                        style={`flex: 0 0 ${shareOf(s, i)}%; background: ${s.color || '#475569'};`}
                        class:missing={s.missing}
                        onclick={() => handleClick(s, i)}
                        onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(s, i)}
                        role={typeof onPointClick === 'function' ? 'button' : undefined}
                        tabindex={typeof onPointClick === 'function' ? 0 : undefined}
                        title={`${s.name} ${fmt(s.data?.[i])}${s.unit || ''}`}
                      ></i>
                    {/each}
                  </div>
                  <small>{p}</small>
                </div>
              {/each}
            </div>
          </section>
        {/if}
      {/each}
    </div>
    {#if totalAssets().length || totalFunding().length}
      <div class="totals">
        {#if totalAssets().length}
          <span>총자산 최신: <b>{fmt(totalAssets()[totalAssets().length - 1])}</b></span>
        {/if}
        {#if totalFunding().length}
          <span>총조달 최신: <b>{fmt(totalFunding()[totalFunding().length - 1])}</b></span>
        {/if}
      </div>
    {/if}
    {#if deltaParts().length}
      <ul class="delta">
        {#each deltaParts() as part}
          <li class={part.tone || ''}>
            <span>{part.label}</span>
            <strong>{fmt(part.value)}<small>{part.unit || ''}</small></strong>
          </li>
        {/each}
      </ul>
    {/if}
  </figure>
{/if}

<style>
  .balance-structure {
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
  .head-stat {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 8px;
  }
  .head-stat span {
    color: #94a3b8;
    font-size: 11px;
  }
  .head-stat strong {
    color: #fb923c;
    font-size: 18px;
    font-weight: 800;
  }
  .head-stat small {
    color: #fb923c;
    font-size: 11px;
    margin-left: 2px;
  }
  .bands {
    display: grid;
    gap: 10px;
  }
  .bands h4 {
    margin: 0 0 4px;
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
  }
  .period-grid {
    display: grid;
    gap: 4px;
  }
  .period {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .stack {
    display: flex;
    height: 64px;
    border-radius: 4px;
    overflow: hidden;
    background: #060b13;
  }
  .stack i {
    display: block;
    cursor: pointer;
  }
  .stack i:hover { filter: brightness(1.2); }
  .stack i.missing { background: repeating-linear-gradient(45deg, #475569 0 4px, transparent 4px 8px) !important; }
  .period small {
    text-align: center;
    color: #64748b;
    font-size: 10px;
  }
  .totals {
    margin-top: 8px;
    display: flex;
    gap: 14px;
    font-size: 11px;
    color: #94a3b8;
  }
  .totals b { color: #f1f5f9; font-weight: 700; }
  .delta {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .delta li {
    border: 1px solid #263145;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 11px;
    background: #070c15;
  }
  .delta li span { color: #94a3b8; margin-right: 6px; }
  .delta li strong { color: #f1f5f9; }
  .delta li.good strong { color: #34d399; }
  .delta li.bad strong { color: #f87171; }
  .delta li.watch strong { color: #fbbf24; }
</style>
