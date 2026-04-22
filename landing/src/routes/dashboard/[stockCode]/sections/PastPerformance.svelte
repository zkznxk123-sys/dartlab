<script>
  // @ts-nocheck
  import Sparkline from './Sparkline.svelte';
  import MiniBars from './MiniBars.svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  const metrics = $derived([
    { key: 'revenue',  title: '매출',     unit: '조원', data: data.revenue,   color: '#fb923c', cagr: data.revenueCAGR,  kind: 'line' },
    { key: 'opIncome', title: '영업이익', unit: '조원', data: data.opIncome,  color: '#ea4647', cagr: data.opIncomeCAGR, kind: 'bars' },
    { key: 'roe',      title: 'ROE',      unit: '%',    data: data.roe,       color: '#fbbf24', cagr: null, kind: 'line' },
    { key: 'debt',     title: '부채비율', unit: '%',    data: data.debtRatio, color: '#34d399', cagr: null, kind: 'line', inverted: true }
  ]);
</script>

<section class="container" id="past">
  <div class="head">
    <div class="eyebrow"><span class="bar"></span>PAST · 과거 5년</div>
    <h2>지난 5년, 이 회사는 무엇을 해왔나</h2>
    <div class="sub">분기별 실적과 재무 건전성의 추세.</div>
  </div>

  <div class="grid">
    {#each metrics as m}
      <div class="card">
        <div class="mh">
          <div>
            <div class="card-title">{m.title}</div>
            <div class="val-row">
              <div class="mono val">
                {m.data[m.data.length - 1].toFixed(1)}
                <span class="unit">{m.unit}</span>
              </div>
              {#if m.cagr !== null}
                <span class="mono cagr {m.cagr >= 0 ? 'green' : 'red'}">
                  {m.cagr >= 0 ? '+' : ''}{m.cagr}%
                  <span class="cagr-label">5Y CAGR</span>
                </span>
              {/if}
            </div>
          </div>
          <div class="mono count">{m.data.length}Q</div>
        </div>

        <div class="chart">
          {#if m.kind === 'bars'}
            <MiniBars data={m.data} width={320} height={80} color={m.color} />
          {:else}
            <Sparkline
              data={m.inverted ? m.data.map((v) => -v) : m.data}
              width={320} height={80} color={m.color}
            />
          {/if}
        </div>

        <div class="mono x-axis">
          <span>20Q1</span><span>24Q4</span>
        </div>
      </div>
    {/each}
  </div>
</section>

<style>
  section { scroll-margin-top: 90px; padding-top: 8px; padding-bottom: 36px; }
  .head { margin-bottom: 20px; }
  .eyebrow {
    font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
    color: var(--orange); text-transform: uppercase;
    display: flex; align-items: center; gap: 8px;
  }
  .bar { width: 18px; height: 1px; background: var(--grad-heat); }
  h2 { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; margin: 6px 0 4px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 14px; max-width: 640px; }

  .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 20px;
    transition: border-color .2s;
  }
  .card:hover { border-color: var(--border-hi); }

  .mh { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
  .val-row { display: flex; align-items: baseline; gap: 10px; margin-top: 8px; }
  .val { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; color: var(--text); }
  .unit { font-size: 13px; color: var(--text-dim); margin-left: 4px; }
  .cagr { font-size: 12px; font-weight: 600; }
  .cagr.green { color: var(--green); }
  .cagr.red { color: var(--red); }
  .cagr-label { color: var(--text-dim); font-weight: 400; }
  .count { font-size: 10px; color: var(--text-faint); letter-spacing: 0.1em; }

  .chart { height: 80px; }
  .x-axis {
    display: flex; justify-content: space-between;
    font-size: 10px; color: var(--text-faint); margin-top: 6px;
  }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
