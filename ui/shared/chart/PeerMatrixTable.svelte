<script>
  // @ts-nocheck
  /**
   * ChartSpec(chartType="peer-matrix") 렌더러.
   *
   * spec.categories = peer corp names (rows)
   * spec.series = [{name: metric, data: [values per peer]}]
   * spec.options.metrics = column labels (== series names 와 동일)
   * spec.options.highlightStockCode = 본 회사 (행 강조)
   * spec.options.rowMeta = [{stockCode, corpName}]
   *
   * 셀 클릭시 onPointClick({stockCode, metric, value, ...}) — peer 회사 페이지
   * 또는 EvidencePanel 진입점.
   *
   * @type {{ spec: object, onPointClick?: (ref: object) => void }}
   */
  let { spec, onPointClick } = $props();

  function metricList() {
    return spec?.options?.metrics ?? (spec?.series ?? []).map((s) => s.name);
  }

  function rowMeta(i) {
    return spec?.options?.rowMeta?.[i] ?? { stockCode: '', corpName: spec?.categories?.[i] ?? '' };
  }

  function cellValue(seriesIdx, rowIdx) {
    const data = spec?.series?.[seriesIdx]?.data;
    return Array.isArray(data) ? data[rowIdx] : null;
  }

  function isHighlight(rowIdx) {
    const code = spec?.options?.highlightStockCode;
    if (!code) return false;
    return rowMeta(rowIdx).stockCode === code;
  }

  function handleClick(rowIdx, metric, value) {
    if (typeof onPointClick !== 'function') return;
    const row = rowMeta(rowIdx);
    onPointClick({
      stockCode: row.stockCode,
      corpName: row.corpName,
      metric,
      value,
      valueRef: `industry:${row.stockCode}:peer:${metric}`
    });
  }

  function fmt(v) {
    if (v == null || !Number.isFinite(v)) return '—';
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  }
</script>

{#if spec?.series?.length && spec?.categories?.length}
  <section class="peer-matrix" aria-label={spec.title}>
    {#if spec.title}
      <header><h3>{spec.title}</h3></header>
    {/if}
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th class="sticky">기업</th>
            {#each metricList() as metric}
              <th>{metric}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each spec.categories as label, rowIdx}
            <tr class:highlight={isHighlight(rowIdx)}>
              <td class="sticky name">{label}</td>
              {#each metricList() as metric, metricIdx}
                {@const v = cellValue(metricIdx, rowIdx)}
                <td
                  class:clickable={typeof onPointClick === 'function'}
                  onclick={() => handleClick(rowIdx, metric, v)}
                  onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(rowIdx, metric, v)}
                  role={typeof onPointClick === 'function' ? 'button' : undefined}
                  tabindex={typeof onPointClick === 'function' ? 0 : undefined}
                >{fmt(v)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>
{/if}

<style>
  .peer-matrix {
    width: 100%;
    border: 1px solid #1e2433;
    border-radius: 7px;
    background: rgba(8, 13, 23, 0.96);
    overflow: hidden;
  }
  header h3 {
    margin: 0;
    padding: 11px 14px 6px;
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
  }
  .scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    color: #cbd5e1;
  }
  th, td {
    padding: 8px 10px;
    text-align: right;
    border-bottom: 1px solid #1e2433;
    white-space: nowrap;
  }
  th {
    color: #94a3b8;
    font-weight: 600;
    background: #060b13;
  }
  th.sticky, td.sticky {
    position: sticky;
    left: 0;
    background: #060b13;
    text-align: left;
  }
  td.name {
    color: #f1f5f9;
    font-weight: 500;
  }
  tr.highlight td {
    background: rgba(251, 146, 60, 0.06);
    color: #fde68a;
  }
  tr.highlight td.name {
    background: rgba(251, 146, 60, 0.12);
    color: #fb923c;
    font-weight: 700;
  }
  td.clickable {
    cursor: pointer;
  }
  td.clickable:hover {
    background: rgba(251, 146, 60, 0.08);
    color: #fb923c;
  }
</style>
