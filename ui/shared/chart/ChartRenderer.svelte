<script>
  // @ts-nocheck
  /**
   * ChartSpec JSON → 적절한 차트 컴포넌트로 dispatch.
   * VSCode webview 전용 — ErrorBoundary 없이 try-catch fallback.
   * @type {{ spec: object, class?: string }}
   */
  let { spec, class: className = '' } = $props();
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
    {:else if spec.chartType === 'radar'}
      {#await import('./RadarChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: RadarChart }}
        <RadarChart {spec} />
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
    {:else if spec.chartType === 'sparkline'}
      {#await import('./SparklineChart.svelte')}
        <p class="chart-loading">차트 준비 중</p>
      {:then { default: SparklineChart }}
        <SparklineChart {spec} />
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
