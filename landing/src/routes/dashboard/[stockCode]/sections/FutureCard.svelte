<script>
  // @ts-nocheck
  import Sparkline from './Sparkline.svelte';

  /** @type {{ data: { future: any, currentPrice: number } }} */
  let { data } = $props();
  const future = $derived(data.future);
  const currentPrice = $derived(data.currentPrice);

  const W = 560, H = 220;
  const padX = 32, padY = 20;
  const w = W - padX * 2, h = H - padY * 2;

  const months = $derived(future.months);
  const step = $derived(w / (months.length - 1));
  const all = $derived([...future.band_hi, ...future.band_lo, currentPrice / 1000]);
  const min = $derived(Math.min(...all) * 0.95);
  const max = $derived(Math.max(...all) * 1.02);
  const range = $derived(max - min);
  const ty = (v) => padY + h - ((v - min) / range) * h;

  function areaPath(hi, lo) {
    let d = '';
    hi.forEach((v, i) => { d += (i === 0 ? 'M' : 'L') + ` ${padX + i * step} ${ty(v)} `; });
    for (let i = lo.length - 1; i >= 0; i--) d += `L ${padX + i * step} ${ty(lo[i])} `;
    return d + 'Z';
  }
  const linePath = (vs) =>
    vs.map((v, i) => (i === 0 ? 'M' : 'L') + ` ${padX + i * step} ${ty(v)}`).join(' ');

  const terminalEps = $derived(future.epsPath[future.epsPath.length - 1]);
  const epsGrowth = $derived(
    (((terminalEps - future.epsPath[0]) / future.epsPath[0]) * 100).toFixed(1)
  );
  const targetPrice = $derived(future.consensus[future.consensus.length - 1] * 1000);
  const expRet = $derived((((targetPrice - currentPrice) / currentPrice) * 100).toFixed(1));
</script>

<div class="card" id="future">
  <div class="head">
    <div>
      <div class="card-title">FUTURE · 12개월 전망</div>
      <h3>7-source 앙상블 포캐스트</h3>
      <div class="sub">증권사 컨센서스, 옵션 임플라이드, 관리자 가이던스, dartlab ML 등 7개 소스 결합.</div>
    </div>
    <div class="legend">
      <span class="leg"><span class="sw" style:background="#fb923c"></span> 컨센서스</span>
      <span class="leg"><span class="sw block" style:background="rgba(234,70,71,0.3)"></span> 90% 신뢰구간</span>
      <span class="leg"><span class="sw dash"></span> 현재가</span>
    </div>
  </div>

  <div class="grid">
    <div>
      <svg viewBox="0 0 {W} {H}" width="100%" style="display:block">
        <defs>
          <linearGradient id="bandGrad" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="#ea4647" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#fb923c" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        {#each [0.25, 0.5, 0.75] as p}
          <line x1={padX} x2={W - padX} y1={padY + h * p} y2={padY + h * p} stroke="rgba(255,255,255,0.04)" stroke-dasharray="2 4"/>
        {/each}

        <line x1={padX} x2={W - padX} y1={ty(currentPrice / 1000)} y2={ty(currentPrice / 1000)}
          stroke="rgba(255,255,255,0.3)" stroke-dasharray="4 4"/>
        <text x={W - padX - 2} y={ty(currentPrice / 1000) - 6} fill="#a6adbb" font-size="9"
          text-anchor="end" font-family="var(--font-mono)">
          현재가 ₩{currentPrice.toLocaleString()}
        </text>

        <path d={areaPath(future.band_hi, future.band_lo)} fill="url(#bandGrad)" />
        <path d={linePath(future.band_hi)} stroke="rgba(234,70,71,0.4)" stroke-width="1" fill="none" stroke-dasharray="2 3"/>
        <path d={linePath(future.band_lo)} stroke="rgba(234,70,71,0.4)" stroke-width="1" fill="none" stroke-dasharray="2 3"/>
        <path d={linePath(future.consensus)} stroke="#fb923c" stroke-width="2" fill="none" stroke-linecap="round"/>
        <circle cx={padX + (future.consensus.length - 1) * step}
          cy={ty(future.consensus[future.consensus.length - 1])}
          r="4" fill="#fb923c" stroke="#0f1219" stroke-width="2"/>

        {#each months as m, i}
          {#if i % 3 === 0 || i === months.length - 1}
            <text x={padX + i * step} y={H - 4}
              fill="#6b7280" font-size="9" text-anchor="middle" font-family="var(--font-mono)">
              {m.replace('26M', '26·').replace('25M', '25·')}
            </text>
          {/if}
        {/each}
      </svg>

      <div class="stat-row">
        <div class="stat">
          <div class="sl">12개월 타겟</div>
          <div class="mono sv" style="color:#fb923c">₩{targetPrice.toLocaleString()}</div>
        </div>
        <div class="stat">
          <div class="sl">기대 수익률</div>
          <div class="mono sv" style="color:var(--green)">+{expRet}%</div>
        </div>
        <div class="stat">
          <div class="sl">소스 수</div>
          <div class="mono sv">7개 · 컨센 95편</div>
        </div>
      </div>
    </div>

    <div class="eps">
      <div class="eps-label">컨센서스 EPS 추이</div>
      <div class="mono eps-val">
        ₩{terminalEps.toLocaleString()}
        <span class="eps-year">26E</span>
      </div>
      <div class="mono eps-growth">+{epsGrowth}% 12M 상향</div>
      <div class="eps-chart">
        <Sparkline data={future.epsPath} width={260} height={70} color="#34d399" fillOpacity={0.15}/>
      </div>
      <hr/>
      <div class="eps-note">
        최근 60일간 <strong style="color:var(--green)">12개 증권사 상향</strong>,
        3개 동결, 1개 하향. HBM 단가 반영 지연이 주요 변수.
      </div>
    </div>
  </div>
</div>

<style>
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 24px; scroll-margin-top: 90px;
  }
  .head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 13px; }
  .legend { display: flex; gap: 14px; font-size: 11px; }
  .leg { display: flex; align-items: center; gap: 6px; color: var(--text-mid); }
  .sw { width: 14px; height: 2px; border-radius: 0; }
  .sw.block { width: 14px; height: 10px; border-radius: 2px; }
  .sw.dash { border-top: 2px dashed rgba(255,255,255,0.4); height: 0; width: 14px; background: transparent !important; }

  .grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 24px; }
  .stat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
  .stat { padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; }
  .sl { font-size: 10px; color: var(--text-dim); letter-spacing: 0.1em; }
  .sv { font-size: 14px; font-weight: 600; margin-top: 3px; color: var(--text); }

  .eps {
    background: rgba(255,255,255,0.02); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 16px;
  }
  .eps-label { font-size: 11px; color: var(--text-dim); letter-spacing: 0.14em; font-weight: 600; }
  .eps-val { font-size: 24px; font-weight: 700; margin-top: 6px; color: var(--text); }
  .eps-year { font-size: 12px; font-weight: 400; color: var(--text-dim); margin-left: 6px; }
  .eps-growth { font-size: 11px; color: var(--green); }
  .eps-chart { margin-top: 12px; height: 70px; }
  hr { border: none; border-top: 1px solid var(--border); margin: 14px 0 12px; }
  .eps-note { font-size: 11px; color: var(--text-mid); line-height: 1.55; }

  @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
</style>
