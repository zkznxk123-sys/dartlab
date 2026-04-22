<script>
  // @ts-nocheck
  /** @type {{ data: { is: any, bs: any, cf: any } }} */
  let { data } = $props();

  let tab = $state('IS');
  let showISTable = $state(false);
  let showBSTable = $state(false);
  let showCFTable = $state(false);

  // ---------- IS dual-axis geometry ----------
  const W_IS = 720, H_IS = 280, padL_IS = 44, padR_IS = 44, padT_IS = 18, padB_IS = 28;
  const w_IS = W_IS - padL_IS - padR_IS, h_IS = H_IS - padT_IS - padB_IS;

  const isYears = $derived(data.is.years);
  const nIS = $derived(isYears.length);
  const maxRev = $derived(Math.max(...data.is.revenue) * 1.1);
  const allProfit = $derived([...data.is.opIncome, ...data.is.netIncome]);
  const maxP = $derived(Math.max(...allProfit) * 1.2);
  const minP = $derived(Math.min(0, Math.min(...allProfit)));
  const rangeP = $derived(maxP - minP);
  const bandW_IS = $derived(w_IS / nIS);
  const barW_IS = $derived(bandW_IS * 0.45);
  const cxIS = (i) => padL_IS + bandW_IS * i + bandW_IS / 2;
  const yL = (v) => padT_IS + h_IS - (v / maxRev) * h_IS;
  const yR = (v) => padT_IS + h_IS - ((v - minP) / rangeP) * h_IS;
  const linePathIS = (vs) =>
    vs.map((v, i) => (i === 0 ? 'M' : 'L') + ` ${cxIS(i)} ${yR(v)}`).join(' ');

  // ---------- CF waterfall ----------
  const cfSteps = $derived([
    { label: '기초 현금', value: data.cf.opening, type: 'total' },
    { label: '영업CF', value: data.cf.operating, type: 'pos' },
    { label: '투자CF', value: data.cf.investing, type: 'neg' },
    { label: '재무CF', value: data.cf.financing, type: 'neg' },
    { label: '환율효과', value: data.cf.fxEffect, type: data.cf.fxEffect >= 0 ? 'pos' : 'neg' },
    { label: '기말 현금', value: data.cf.closing, type: 'total' }
  ]);

  const W_CF = 720, H_CF = 280, padL_CF = 20, padR_CF = 20, padT_CF = 30, padB_CF = 40;
  const w_CF = W_CF - padL_CF - padR_CF, h_CF = H_CF - padT_CF - padB_CF;
  const nCF = $derived(cfSteps.length);
  const bandW_CF = $derived(w_CF / nCF);
  const barW_CF = $derived(bandW_CF * 0.55);

  const cfBars = $derived.by(() => {
    let running = 0;
    return cfSteps.map((s) => {
      if (s.type === 'total') { running = s.value; return { ...s, from: 0, to: s.value }; }
      const from = running; const to = running + s.value; running = to;
      return { ...s, from, to };
    });
  });

  const allVals = $derived([
    data.cf.opening, data.cf.closing,
    data.cf.opening + data.cf.operating,
    data.cf.opening + data.cf.operating + data.cf.investing
  ]);
  const minVal = $derived(Math.min(0, ...allVals));
  const maxVal = $derived(Math.max(...allVals) * 1.1);
  const rangeVal = $derived(maxVal - minVal);
  const yPos = (v) => padT_CF + h_CF - ((v - minVal) / rangeVal) * h_CF;

  // ---------- BS stacks ----------
  const assetLabels = { cash: '현금성', receivables: '매출채권', inventory: '재고자산', tangible: '유형자산', intangible: '무형자산', other: '기타' };
  const liabLabels  = { payables: '매입채무', shortDebt: '단기차입', longDebt: '장기차입', bonds: '사채', provisions: '충당부채', other: '기타' };
  const eqLabels    = { paidIn: '자본금', capitalSurplus: '자본잉여금', retained: '이익잉여금', otherComp: '기포손', treasury: '자기주식' };

  const assetPalette = ['#34d399','#60a5fa','#fbbf24','#fb923c','#a78bfa','#6b7280'];
  const liabPalette  = ['#ea4647','#f97316','#ef4444','#b91c1c','#fbbf24','#6b7280'];
  const eqPalette    = ['#60a5fa','#a78bfa','#fb923c','#34d399','#6b7280'];
</script>

<div class="card" id="financials">
  <div class="head">
    <div>
      <div class="card-title">FINANCIALS · 재무제표 원본</div>
      <h3>IS · BS · CF, 시각화 + 원본 표</h3>
      <div class="sub">K-IFRS 정규화 · Bridge Matching 적용 · 연결재무제표 기준</div>
    </div>
    <div class="tabs">
      {#each ['IS', 'BS', 'CF'] as t}
        <button class="tab" class:active={tab === t} onclick={() => (tab = t)}>
          {#if t === 'IS'}손익 · IS{:else if t === 'BS'}재무상태 · BS{:else}현금흐름 · CF{/if}
        </button>
      {/each}
    </div>
  </div>

  {#if tab === 'IS'}
    <svg viewBox="0 0 {W_IS} {H_IS}" width="100%" style="display:block">
      <defs>
        <linearGradient id="isBar" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#ea4647" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="#fb923c" stop-opacity="0.5"/>
        </linearGradient>
      </defs>
      {#each [0.25, 0.5, 0.75, 1] as p}
        <line x1={padL_IS} x2={W_IS - padR_IS}
          y1={padT_IS + h_IS * (1 - p)} y2={padT_IS + h_IS * (1 - p)}
          stroke="rgba(255,255,255,0.04)" stroke-dasharray="2 4"/>
      {/each}
      {#each [0, maxRev / 2, maxRev] as v}
        <text x={padL_IS - 6} y={yL(v) + 3} font-size="9" fill="#6b7280"
          text-anchor="end" font-family="var(--font-mono)">{v.toFixed(0)}</text>
      {/each}
      {#each [minP, (minP + maxP) / 2, maxP] as v}
        <text x={W_IS - padR_IS + 6} y={yR(v) + 3} font-size="9" fill="#6b7280"
          text-anchor="start" font-family="var(--font-mono)">{v.toFixed(0)}</text>
      {/each}
      <text x={padL_IS - 6} y={padT_IS - 4} font-size="9" fill="#a6adbb" text-anchor="end" font-family="var(--font-mono)">매출 (조원)</text>
      <text x={W_IS - padR_IS + 6} y={padT_IS - 4} font-size="9" fill="#a6adbb" text-anchor="start" font-family="var(--font-mono)">이익 (조원)</text>
      <line x1={padL_IS} x2={W_IS - padR_IS} y1={yR(0)} y2={yR(0)} stroke="rgba(255,255,255,0.1)"/>
      {#each data.is.revenue as v, i}
        <rect x={cxIS(i) - barW_IS / 2} y={yL(v)} width={barW_IS}
          height={padT_IS + h_IS - yL(v)} fill="url(#isBar)" rx="2"/>
      {/each}
      {#each data.is.revenue as v, i}
        <text x={cxIS(i)} y={yL(v) - 6} font-size="10" fill="#e8ecf5"
          text-anchor="middle" font-family="var(--font-mono)" font-weight="600">{v.toFixed(0)}</text>
      {/each}
      <path d={linePathIS(data.is.opIncome)} stroke="#34d399" stroke-width="2" fill="none" stroke-linecap="round"/>
      {#each data.is.opIncome as v, i}
        <circle cx={cxIS(i)} cy={yR(v)} r="4" fill="#34d399" stroke="#0f1219" stroke-width="2"/>
      {/each}
      <path d={linePathIS(data.is.netIncome)} stroke="#fbbf24" stroke-width="2" fill="none" stroke-linecap="round" stroke-dasharray="5 3"/>
      {#each data.is.netIncome as v, i}
        <circle cx={cxIS(i)} cy={yR(v)} r="3.5" fill="#fbbf24" stroke="#0f1219" stroke-width="2"/>
      {/each}
      {#each isYears as y, i}
        <text x={cxIS(i)} y={H_IS - 8} font-size="11" fill="#a6adbb"
          text-anchor="middle" font-family="var(--font-mono)">{y}</text>
      {/each}
    </svg>
    <div class="legend-row">
      <span class="leg"><span class="sw bar heat"></span>매출 (좌축)</span>
      <span class="leg"><span class="sw line" style:background="#34d399"></span>영업이익 (우축)</span>
      <span class="leg"><span class="sw dash" style:border-top="2px dashed #fbbf24"></span>당기순이익 (우축)</span>
      <button class="table-toggle" onclick={() => (showISTable = !showISTable)}>
        {showISTable ? '표 접기 ▲' : '원본 표 보기 ▼'}
      </button>
    </div>
    {#if showISTable}
      <table class="raw mono">
        <thead>
          <tr><th>계정</th>{#each isYears as y}<th>{y}</th>{/each}</tr>
        </thead>
        <tbody>
          <tr class="bold"><td>매출액</td>{#each data.is.revenue as v}<td>{v.toFixed(1)}</td>{/each}</tr>
          <tr><td>영업이익</td>{#each data.is.opIncome as v}<td>{v.toFixed(1)}</td>{/each}</tr>
          <tr><td>당기순이익</td>{#each data.is.netIncome as v}<td>{v.toFixed(1)}</td>{/each}</tr>
          <tr><td>영업이익률</td>{#each data.is.opMargin as v}<td>{v.toFixed(1)}%</td>{/each}</tr>
        </tbody>
      </table>
    {/if}

  {:else if tab === 'BS'}
    <div class="bs-grid">
      {@render stack('자산 구조', data.bs.assets, data.bs.years, assetLabels, assetPalette, '#34d399')}
      {@render stack('부채 구조', data.bs.liabilities, data.bs.years, liabLabels, liabPalette, '#ef4444')}
      {@render stack('자본 구조', data.bs.equity, data.bs.years, eqLabels, eqPalette, '#60a5fa')}
    </div>
    <div class="legend-row right-only">
      <button class="table-toggle" onclick={() => (showBSTable = !showBSTable)}>
        {showBSTable ? '표 접기 ▲' : '원본 표 보기 ▼'}
      </button>
    </div>
    {#if showBSTable}
      {@render rawBlock('자산 (조원)', data.bs.assets, data.bs.years)}
      {@render rawBlock('부채 (조원)', data.bs.liabilities, data.bs.years)}
      {@render rawBlock('자본 (조원)', data.bs.equity, data.bs.years)}
    {/if}

  {:else}
    <svg viewBox="0 0 {W_CF} {H_CF}" width="100%" style="display:block">
      <line x1={padL_CF} x2={W_CF - padR_CF} y1={yPos(0)} y2={yPos(0)} stroke="rgba(255,255,255,0.1)"/>
      {#each cfBars as b, i}
        {@const x = padL_CF + bandW_CF * i + (bandW_CF - barW_CF) / 2}
        {@const yTop = yPos(Math.max(b.from, b.to))}
        {@const yBot = yPos(Math.min(b.from, b.to))}
        {@const color = b.type === 'total' ? '#60a5fa' : b.type === 'pos' ? '#34d399' : '#ef4444'}
        {#if i > 0}
          <line
            x1={padL_CF + bandW_CF * (i - 1) + (bandW_CF + barW_CF) / 2}
            x2={x}
            y1={yPos(cfBars[i - 1].to)} y2={yPos(cfBars[i - 1].to)}
            stroke="rgba(255,255,255,0.15)" stroke-dasharray="2 3"/>
        {/if}
        <rect x={x} y={yTop} width={barW_CF} height={Math.max(2, yBot - yTop)}
          fill={color} opacity="0.85" rx="2"/>
        <text x={x + barW_CF / 2} y={yTop - 6} font-size="11" fill="#e8ecf5"
          text-anchor="middle" font-family="var(--font-mono)" font-weight="600">
          {b.value > 0 && b.type !== 'total' ? '+' : ''}{b.value.toFixed(1)}
        </text>
        <text x={x + barW_CF / 2} y={H_CF - 18} font-size="11" fill="#a6adbb"
          text-anchor="middle" font-weight="500">{b.label}</text>
        <text x={x + barW_CF / 2} y={H_CF - 6} font-size="9" fill="#6b7280"
          text-anchor="middle" font-family="var(--font-mono)">FY{data.cf.year}</text>
      {/each}
    </svg>
    <div class="legend-row">
      <span class="leg"><span class="sw bar" style:background="#60a5fa"></span>기초·기말 잔액</span>
      <span class="leg"><span class="sw bar" style:background="#34d399"></span>유입 (+)</span>
      <span class="leg"><span class="sw bar" style:background="#ef4444"></span>유출 (−)</span>
      <button class="table-toggle" onclick={() => (showCFTable = !showCFTable)}>
        {showCFTable ? '표 접기 ▲' : '원본 표 보기 ▼'}
      </button>
    </div>
    {#if showCFTable}
      <table class="raw mono">
        <thead><tr><th>계정</th><th>{data.cf.year}</th></tr></thead>
        <tbody>
          <tr><td>기초 현금및현금성자산</td><td>{data.cf.opening.toFixed(1)}</td></tr>
          <tr><td>영업활동 현금흐름</td><td>{data.cf.operating.toFixed(1)}</td></tr>
          <tr><td>투자활동 현금흐름</td><td class="neg">({Math.abs(data.cf.investing).toFixed(1)})</td></tr>
          <tr><td>재무활동 현금흐름</td><td class="neg">({Math.abs(data.cf.financing).toFixed(1)})</td></tr>
          <tr><td>환율변동 효과</td><td>{data.cf.fxEffect.toFixed(1)}</td></tr>
          <tr class="bold"><td>기말 현금및현금성자산</td><td>{data.cf.closing.toFixed(1)}</td></tr>
        </tbody>
      </table>
    {/if}
  {/if}
</div>

{#snippet stack(title, dict, years, labels, palette, accent)}
  {@const keys = Object.keys(dict)}
  {@const W = 280}
  {@const H = 200}
  {@const padL = 8}
  {@const padR = 8}
  {@const padT = 8}
  {@const padB = 24}
  {@const w = W - padL - padR}
  {@const h = H - padT - padB}
  {@const bandW = w / years.length}
  {@const barW = bandW * 0.55}
  {@const totals = years.map((_, i) => keys.reduce((s, k) => s + Math.max(0, dict[k][i]), 0))}
  {@const maxTotal = Math.max(...totals) * 1.05}

  <div class="stack-panel">
    <div class="stack-head">
      <span class="stack-title">{title}</span>
      <span class="mono stack-total" style:color={accent}>
        {totals[totals.length - 1].toFixed(0)}조
      </span>
    </div>
    <svg viewBox="0 0 {W} {H}" width="100%" style="display:block">
      {#each years as yr, i}
        {@const barX = padL + bandW * i + (bandW - barW) / 2}
        {@const segs = (() => {
          let acc = 0;
          return keys.map((k, ki) => {
            const v = dict[k][i];
            if (v <= 0) return null;
            const barH = (v / maxTotal) * h;
            const y = padT + h - ((acc + v) / maxTotal) * h;
            acc += v;
            return { y, barH, color: palette[ki] };
          });
        })()}
        <g>
          {#each segs as seg}
            {#if seg}
              <rect x={barX} y={seg.y} width={barW} height={seg.barH}
                fill={seg.color} opacity="0.82"/>
            {/if}
          {/each}
          <text x={barX + barW / 2} y={H - 8} font-size="9" fill="#6b7280"
            text-anchor="middle" font-family="var(--font-mono)">{yr}</text>
        </g>
      {/each}
    </svg>
    <div class="stack-legend">
      {#each keys as k, i}
        <span class="sl-item">
          <span class="sl-sw" style:background={palette[i]}></span>{labels[k]}
        </span>
      {/each}
    </div>
  </div>
{/snippet}

{#snippet rawBlock(title, dict, years)}
  <div class="raw-section-title">{title}</div>
  <table class="raw mono">
    <thead><tr><th>계정</th>{#each years as y}<th>{y}</th>{/each}</tr></thead>
    <tbody>
      {#each Object.entries(dict) as [k, arr]}
        <tr>
          <td>{k}</td>
          {#each arr as v}
            <td class:neg={v < 0}>{v < 0 ? `(${Math.abs(v).toFixed(1)})` : v.toFixed(1)}</td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
{/snippet}

<style>
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 24px; scroll-margin-top: 90px;
  }
  .head { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 13px; }

  .tabs {
    display: flex; gap: 4px; padding: 4px;
    background: rgba(255,255,255,0.03); border: 1px solid var(--border);
    border-radius: 10px;
  }
  .tab {
    padding: 8px 16px; border-radius: 7px; font-size: 12px; font-weight: 600;
    background: transparent; color: var(--text-mid); border: none; cursor: pointer;
    transition: all .15s;
  }
  .tab.active { background: var(--grad-heat); color: #fff; }

  .legend-row {
    display: flex; gap: 18px; justify-content: center; flex-wrap: wrap;
    padding-top: 10px; border-top: 1px solid var(--border); margin-top: 14px;
  }
  .legend-row.right-only { justify-content: flex-end; }
  .leg { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-mid); }
  .sw { display: inline-block; }
  .sw.bar { width: 14px; height: 10px; border-radius: 2px; }
  .sw.bar.heat { background: linear-gradient(180deg, #ea4647, #fb923c); }
  .sw.line { width: 16px; height: 2px; border-radius: 2px; }
  .sw.dash { width: 16px; height: 0; }
  .table-toggle {
    margin-left: auto; font-size: 11px; color: var(--text-mid);
    text-decoration: underline dotted; background: transparent; border: none; cursor: pointer;
  }

  .raw {
    width: 100%; border-collapse: collapse; font-size: 12px;
    margin-top: 14px; overflow: auto;
    border: 1px solid var(--border); border-radius: 8px;
  }
  .raw th {
    padding: 10px 14px; text-align: right; font-weight: 600;
    color: var(--text-dim); letter-spacing: 0.08em; font-size: 10px;
    background: rgba(255,255,255,0.03);
  }
  .raw th:first-child { text-align: left; }
  .raw td { padding: 9px 14px; text-align: right; color: var(--text); border-top: 1px solid var(--border); }
  .raw td:first-child { text-align: left; color: var(--text-mid); font-family: var(--font-ui); }
  .raw tr.bold td { font-weight: 700; color: var(--text); }
  .raw td.neg { color: var(--red); }
  .raw-section-title {
    font-size: 11px; font-weight: 700; color: var(--text-dim);
    letter-spacing: 0.1em; margin-top: 18px; margin-bottom: 6px;
  }

  .bs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .stack-panel {
    border: 1px solid var(--border); border-radius: var(--r-md);
    padding: 14px; background: rgba(255,255,255,0.02);
  }
  .stack-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .stack-title { font-size: 12px; font-weight: 700; letter-spacing: 0.04em; color: var(--text); }
  .stack-total { font-size: 11px; font-weight: 600; }
  .stack-legend { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .sl-item { display: flex; align-items: center; gap: 4px; font-size: 10px; color: var(--text-mid); }
  .sl-sw { width: 8px; height: 8px; border-radius: 2px; }

  @media (max-width: 960px) { .bs-grid { grid-template-columns: 1fr; } }
</style>
