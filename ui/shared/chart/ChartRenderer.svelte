<script>
  // @ts-nocheck
  /**
   * ChartSpec JSON → 적절한 차트 컴포넌트로 dispatch.
   * dartlab.viz 의 단일 시각화 SSOT 진입점 — VSCode webview · landing · notebook
   * 모두 같은 컴포넌트로 렌더한다.
   *
   * onPointClick 이 주어지면 series.data[i] 의 pointRefs[i] 를 인자로 받는다.
   * landing 의 EvidencePanel drill-back 회로의 진입점.
   *
   * @type {{ spec: object, class?: string, onPointClick?: (ref: object) => void }}
   */
  let { spec, class: className = '', onPointClick } = $props();
</script>

{#if spec}
  <div class="dl-chart-container chart-{spec.chartType ?? spec.vizType ?? 'unknown'} {className}">
    {#if spec.vizType === 'diagram' && spec.diagramType === 'mermaid'}
      <div class="mermaid-block">
        {#if spec.title}
          <div class="mermaid-title">{spec.title}</div>
        {/if}
        <pre class="mermaid-source">{spec.source}</pre>
        <button class="mermaid-copy" onclick={() => navigator.clipboard.writeText(spec.source)} title="복사">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 11V3h8"/></svg>
        </button>
      </div>
    {:else if spec.chartType === 'combo' || spec.chartType === 'bar' || spec.chartType === 'line'}
      {#await import('./TrendChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: TrendChart }}
        <TrendChart {spec} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'radar' || spec.chartType === 'six-act-radar'}
      {#await import('./RadarChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: RadarChart }}
        <RadarChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'waterfall'}
      {#await import('./WaterfallChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: WaterfallChart }}
        <WaterfallChart {spec} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'heatmap'}
      {#await import('./HeatmapChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: HeatmapChart }}
        <HeatmapChart {spec} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'sparkline' || spec.chartType === 'hover-spark'}
      {#await import('./SparklineChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: SparklineChart }}
        <SparklineChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'pie'}
      {#await import('./PieChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: PieChart }}
        <PieChart {spec} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'kpi-ribbon'}
      {#await import('./KpiRibbonChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: KpiRibbonChart }}
        <KpiRibbonChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'peer-matrix'}
      {#await import('./PeerMatrixTable.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: PeerMatrixTable }}
        <PeerMatrixTable {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'evidence-coverage'}
      {#await import('./EvidenceCoverage.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: EvidenceCoverage }}
        <EvidenceCoverage {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'income-trend-matrix'}
      {#await import('./IncomeTrendMatrixChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: IncomeTrendMatrixChart }}
        <IncomeTrendMatrixChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'balance-structure-trend'}
      {#await import('./BalanceStructureTrendChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: BalanceStructureTrendChart }}
        <BalanceStructureTrendChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else if spec.chartType === 'cashflow-signed-matrix'}
      {#await import('./CashflowSignedMatrixChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: CashflowSignedMatrixChart }}
        <CashflowSignedMatrixChart {spec} {onPointClick} />
      {:catch}
        <p class="chart-unsupported">차트를 표시할 수 없습니다.</p>
      {/await}
    {:else}
      <p class="chart-unsupported">지원하지 않는 차트 타입: {spec.chartType ?? spec.vizType}</p>
    {/if}
  </div>
{/if}

<style>
  .dl-chart-container {
    width: 100%;
    min-height: 200px;
    margin: 8px 0;
  }
  .chart-sparkline {
    min-height: 0;
  }
  .chart-unsupported {
    font-size: 12px;
    color: var(--vscode-descriptionForeground, #888);
  }
  .chart-loading {
    min-height: 180px;
    display: grid;
    place-items: center;
    font-size: 12px;
    color: var(--vscode-descriptionForeground, #888);
    border: 1px dashed rgba(148, 163, 184, 0.25);
    border-radius: 6px;
  }
  .mermaid-block {
    position: relative;
  }
  .mermaid-title {
    font-size: 12px;
    font-weight: 500;
    color: var(--vscode-foreground, #ccc);
    margin-bottom: 4px;
  }
  .mermaid-source {
    font-size: 11px;
    padding: 12px;
    background: var(--vscode-editor-background, #1e1e1e);
    border: 1px solid var(--vscode-panel-border, #333);
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.5;
    color: var(--vscode-editor-foreground, #d4d4d4);
  }
  .mermaid-copy {
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 4px;
    border-radius: 4px;
    background: transparent;
    border: none;
    color: var(--vscode-descriptionForeground, #888);
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.15s;
  }
  .mermaid-block:hover .mermaid-copy {
    opacity: 1;
  }
  .mermaid-copy:hover {
    background: var(--vscode-toolbar-hoverBackground, #333);
  }
</style>
