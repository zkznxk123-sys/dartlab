<script>
  // @ts-nocheck
  /** @type {{ data: any }} */
  let { data: supply } = $props();
  const hhiPct = $derived(Math.min(100, (supply.hhi / 4000) * 100));
</script>

<div id="supply" class="wrap">
  <div class="panel">
    <div class="badge">
      <span class="pulse"></span> DARTLAB ONLY
    </div>

    <div class="card-title">SUPPLY CHAIN · 공급망</div>
    <h3>누가 이 회사의 위험이고, 누가 기회인가</h3>
    <div class="sub">K-IFRS 주석 · 사업보고서에서 추출한 공급사/고객 집중도.</div>

    <div class="grid">
      {@render tbl('상위 공급사', 'supplier', supply.suppliers)}
      {@render tbl('상위 고객', 'customer', supply.customers)}

      <div class="hhi">
        <div class="hl">HHI 집중도</div>
        <div class="mono hv">{supply.hhi.toLocaleString()}</div>
        <div class="hlbl">{supply.hhiLabel}</div>

        <div class="gauge-wrap">
          <div class="gauge"></div>
          <div class="marker-wrap"><div class="marker" style:left="{hhiPct}%"></div></div>
          <div class="gauge-labels mono">
            <span>분산</span><span>1,500</span><span>2,500</span><span>독점</span>
          </div>
        </div>

        <div class="hhi-note">
          <span class="warn-txt">⚠ Apple 단일 고객 18.7%</span> — 분기 아이폰 사이클 연동 위험.
        </div>
      </div>
    </div>

    <a href="#" class="cta">
      <div>
        <div class="cta-eyebrow">DARTLAB 산업지도</div>
        <div class="cta-title">이 회사를 중심으로 한 2,664사 네트워크 전체 보기</div>
      </div>
      <div class="cta-btn">
        네트워크 열기
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 7H11M7 3L11 7L7 11" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </a>
  </div>
</div>

{#snippet tbl(title, kind, rows)}
  {@const isCustomer = kind === 'customer'}
  {@const color = isCustomer ? '#34d399' : '#fb923c'}
  <div class="tbl">
    <div class="tbl-head">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        {#if isCustomer}
          <path d="M2 7L7 2L12 7L7 12L2 7Z" stroke={color} stroke-width="1.5"/>
        {:else}
          <circle cx="7" cy="7" r="4.5" stroke={color} stroke-width="1.5"/>
        {/if}
      </svg>
      <span class="tbl-title">{title}</span>
      <span class="mono tbl-top">TOP 5</span>
    </div>
    <div class="rows">
      {#each rows as r, i}
        <div class="row" style:border-bottom={i < rows.length - 1 ? '1px solid var(--border)' : 'none'}>
          <span class="mono idx">#{i + 1}</span>
          <div>
            <div class="rn">{r.name}</div>
            <div class="rr">{r.role}</div>
          </div>
          <div class="bar-row">
            <div class="rtrack"><div class="rfill" style:width="{Math.min(100, r.share * 5)}%" style:background={color}></div></div>
            <span class="mono rpct" style:color={color}>{r.share}%</span>
          </div>
        </div>
      {/each}
    </div>
  </div>
{/snippet}

<style>
  .wrap { scroll-margin-top: 90px; }
  .panel {
    background: linear-gradient(135deg, rgba(234,70,71,0.08) 0%, rgba(15,18,25,1) 60%);
    border: 1px solid var(--border-accent);
    border-radius: var(--r-lg); padding: 24px;
    position: relative; overflow: hidden;
  }
  .badge {
    position: absolute; top: 20px; right: 20px;
    display: flex; align-items: center; gap: 6px;
    font-size: 10px; letter-spacing: 0.14em; font-weight: 700;
    color: var(--orange); padding: 4px 10px;
    border: 1px solid var(--border-accent); border-radius: 999px;
    background: rgba(234,70,71,0.08);
  }
  .pulse { width: 5px; height: 5px; border-radius: 50%; background: var(--grad-heat); box-shadow: 0 0 8px var(--orange); }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 13px; margin-bottom: 22px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr 0.8fr; gap: 18px; }

  .tbl {
    padding: 18px; border: 1px solid var(--border);
    border-radius: var(--r-md); background: rgba(255,255,255,0.02);
  }
  .tbl-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  .tbl-title { font-size: 12px; font-weight: 600; letter-spacing: 0.04em; color: var(--text); }
  .tbl-top { margin-left: auto; font-size: 10px; color: var(--text-dim); }
  .rows { display: flex; flex-direction: column; gap: 2px; }
  .row {
    display: grid; grid-template-columns: 18px 1fr auto;
    align-items: center; gap: 10px; padding: 8px 0;
  }
  .idx { font-size: 10px; color: var(--text-faint); }
  .rn { font-size: 13px; font-weight: 600; color: var(--text); }
  .rr { font-size: 11px; color: var(--text-dim); }
  .bar-row { display: flex; align-items: center; gap: 8px; }
  .rtrack { width: 40px; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; }
  .rfill { height: 100%; border-radius: 2px; }
  .rpct { font-size: 12px; font-weight: 600; width: 40px; text-align: right; }

  .hhi {
    padding: 18px; border: 1px solid var(--border); border-radius: var(--r-md);
    background: rgba(255,255,255,0.02); display: flex; flex-direction: column;
  }
  .hl { font-size: 11px; color: var(--text-dim); letter-spacing: 0.1em; font-weight: 600; }
  .hv { font-size: 40px; font-weight: 700; letter-spacing: -0.03em; margin-top: 6px; line-height: 1; color: var(--text); }
  .hlbl { font-size: 12px; color: var(--yellow); font-weight: 600; margin-top: 4px; }
  .gauge-wrap { margin-top: 18px; }
  .gauge {
    position: relative; height: 8px; border-radius: 4px;
    background: linear-gradient(90deg, #34d399 0%, #34d399 37%, #fbbf24 37%, #fbbf24 62%, #ef4444 62%, #ef4444 100%);
    opacity: 0.4;
  }
  .marker-wrap { position: relative; margin-top: -12px; }
  .marker {
    position: absolute; top: 0; width: 3px; height: 16px;
    background: #fff; transform: translateX(-50%);
    border-radius: 2px; box-shadow: 0 0 10px rgba(255,255,255,0.7);
  }
  .gauge-labels { display: flex; justify-content: space-between; font-size: 9px; color: var(--text-faint); margin-top: 8px; }
  .hhi-note { margin-top: auto; padding-top: 18px; font-size: 11px; color: var(--text-mid); line-height: 1.5; }
  .warn-txt { color: var(--yellow); font-weight: 600; }

  .cta {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    margin-top: 20px; padding: 18px 22px;
    background: var(--grad-heat); border-radius: var(--r-md); color: #fff;
    box-shadow: 0 8px 24px rgba(234,70,71,0.25);
    text-decoration: none;
  }
  .cta-eyebrow { font-size: 10px; letter-spacing: 0.14em; opacity: 0.85; font-weight: 600; }
  .cta-title { font-size: 17px; font-weight: 700; letter-spacing: -0.01em; margin-top: 3px; }
  .cta-btn {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 16px; background: rgba(255,255,255,0.18);
    border-radius: 8px; font-size: 13px; font-weight: 600;
    border: 1px solid rgba(255,255,255,0.25);
  }

  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
</style>
