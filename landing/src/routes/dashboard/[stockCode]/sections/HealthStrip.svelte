<script>
  // @ts-nocheck
  /** @type {{ data: { key:string,label:string,status:'pass'|'fail'|'warn',note:string }[] }} */
  let { data } = $props();

  const color = { pass: '#34d399', fail: '#ef4444', warn: '#fbbf24' };
  const label = { pass: '통과', fail: '주의', warn: '주의' };

  const jumpMap = {
    profit: 'past', growth: 'past', stable: 'health',
    quality: 'past', gov: 'thesis', macro: 'future'
  };

  function jump(key) {
    const id = jumpMap[key] || key;
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
</script>

<section class="container reveal">
  <div class="grid">
    {#each data as it, i}
      <button class="item" onclick={() => jump(it.key)} style:border-right={i < data.length - 1 ? '1px solid var(--border)' : 'none'}>
        <div class="icon" style:background={color[it.status] + '1a'} style:border-color={color[it.status] + '40'}>
          {#if it.status === 'pass'}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8L6.5 11.5L13 4.5" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          {:else if it.status === 'fail'}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 4L12 12M12 4L4 12" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
            </svg>
          {:else}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 2L14.5 13H1.5L8 2Z" stroke="#fbbf24" stroke-width="1.6" stroke-linejoin="round"/>
              <path d="M8 6.5V9.5M8 11.5V11.7" stroke="#fbbf24" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          {/if}
        </div>
        <div class="body">
          <div class="title-row">
            <span class="title">{it.label}</span>
            <span class="tag" style:color={color[it.status]}>{label[it.status]}</span>
          </div>
          <div class="note">{it.note}</div>
        </div>
      </button>
    {/each}
  </div>
</section>

<style>
  section { padding-top: 8px; padding-bottom: 36px; }
  .grid {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 8px;
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 4px;
    overflow-x: auto;
  }
  .item {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 16px; border-radius: 10px;
    text-align: left; background: transparent; border: none;
    color: inherit; cursor: pointer; min-width: 0;
    transition: background .15s;
  }
  .item:hover { background: rgba(255,255,255,0.03); }
  .icon {
    width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
    display: grid; place-items: center; border: 1px solid;
  }
  .body { min-width: 0; flex: 1; }
  .title-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px; }
  .title { font-size: 14px; font-weight: 600; color: var(--text); }
  .tag { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; }
  .note {
    font-size: 11px; color: var(--text-dim); line-height: 1.4;
    overflow: hidden; text-overflow: ellipsis;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }
  @media (max-width: 900px) { .grid { grid-template-columns: repeat(3, 1fr); } }
  @media (max-width: 560px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
