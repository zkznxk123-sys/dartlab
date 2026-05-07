<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="evidence-coverage") 렌더러.
   *
   * spec.series[0].items = [{label, status, source, url, ...}]
   * status: 'ready' | 'lazy' | 'fallback' | 'missing' | 'waiting'
   *
   * 칩 클릭시 onPointClick({label, status, source, url}).
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  function items() {
    return spec?.series?.[0]?.items ?? [];
  }

  function statusLabel(s) {
    switch (s) {
      case 'ready': return '준비됨';
      case 'lazy': return '필요 시 로드';
      case 'fallback': return '요약 사용';
      case 'waiting': return '대기';
      case 'missing': return '없음';
      default: return s ?? '';
    }
  }

  function handleClick(item) {
    if (typeof onPointClick === 'function') onPointClick(item);
  }
</script>

{#if items().length}
  <section class="evidence-coverage" aria-label={spec.title}>
    {#if spec.title}
      <header><h3>{spec.title}</h3></header>
    {/if}
    <ul>
      {#each items() as item}
        <li
          class="status-{item.status || 'unknown'}"
          class:clickable={typeof onPointClick === 'function'}
          onclick={() => handleClick(item)}
          onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(item)}
          role={typeof onPointClick === 'function' ? 'button' : undefined}
          tabindex={typeof onPointClick === 'function' ? 0 : undefined}
        >
          <span class="dot" aria-hidden="true"></span>
          <span class="label">{item.label}</span>
          <span class="status">{statusLabel(item.status)}</span>
          {#if item.source}<span class="source">{item.source}</span>{/if}
        </li>
      {/each}
    </ul>
  </section>
{/if}

<style>
  .evidence-coverage {
    width: 100%;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: rgba(8, 13, 23, 0.96);
    padding: 11px 14px;
  }
  header h3 {
    margin: 0 0 8px;
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 6px;
  }
  li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 9px;
    border: 1px solid #263145;
    border-radius: 6px;
    background: #070c15;
    color: #cbd5e1;
    font-size: 11px;
    text-align: left;
  }
  li.clickable { cursor: pointer; }
  li.clickable:hover { border-color: #fb923c; }
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #64748b;
    flex-shrink: 0;
  }
  li.status-ready .dot { background: #34d399; }
  li.status-lazy .dot, li.status-waiting .dot { background: #fbbf24; }
  li.status-fallback .dot { background: #60a5fa; }
  li.status-missing .dot { background: #ef4444; }
  .label {
    flex: 1 1 auto;
    color: #f1f5f9;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .status {
    color: #94a3b8;
  }
  .source {
    color: #64748b;
    font-size: 10px;
  }
</style>
