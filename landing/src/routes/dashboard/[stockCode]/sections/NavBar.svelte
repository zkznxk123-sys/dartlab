<script>
  // @ts-nocheck
  import { onMount } from 'svelte';

  /** @type {{ data?: { version?: string, logoSrc?: string } }} */
  let { data = {} } = $props();

  let scrolled = $state(false);

  onMount(() => {
    const on = () => (scrolled = window.scrollY > 40);
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  });

  const navItems = [
    { label: '엔진', icon: 'engine', href: '#engines' },
    { label: '재무제표', icon: 'sheet', href: '#financials' },
    { label: '산업지도', icon: 'map', href: '#supply' },
    { label: '블로그', icon: 'book' }
  ];

  function jump(href) {
    if (!href) return;
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
</script>

<nav class="nav" class:scrolled>
  <div class="container nav-inner">
    <a href="/" class="logo">
      <div class="logo-badge">
        {#if data.logoSrc}
          <img src={data.logoSrc} alt="dartlab" />
        {:else}
          <svg width="18" height="18" viewBox="0 0 14 14">
            <circle cx="7" cy="7" r="5.5" fill="none" stroke="#fb923c" stroke-width="1.5" />
            <circle cx="7" cy="7" r="2" fill="#fb923c" />
          </svg>
        {/if}
      </div>
      <div class="logo-text">
        <span class="brand">dartlab</span>
        <span class="mono ver">{data.version ?? 'v0.2.4'}</span>
      </div>
    </a>

    <div class="nav-items">
      {#each navItems as it}
        <button class="btn btn-ghost" onclick={() => jump(it.href)}>
          {#if it.icon === 'engine'}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="7" cy="7" r="2.2"/><path d="M7 1v2M7 11v2M1 7h2M11 7h2M2.76 2.76l1.42 1.42M9.83 9.83l1.4 1.4M11.24 2.76l-1.42 1.42M4.17 9.83l-1.4 1.4"/></svg>
          {:else if it.icon === 'sheet'}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="1.5" width="10" height="11" rx="1"/><path d="M4.5 4.5H9.5M4.5 7H9.5M4.5 9.5H7"/></svg>
          {:else if it.icon === 'map'}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M1 3L5 1.5L9 3L13 1.5V11L9 12.5L5 11L1 12.5V3Z"/><path d="M5 1.5V11M9 3V12.5"/></svg>
          {:else if it.icon === 'book'}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M2 2.5H6C6.55 2.5 7 2.95 7 3.5V12C7 11.45 6.55 11 6 11H2V2.5Z"/><path d="M12 2.5H8C7.45 2.5 7 2.95 7 3.5V12C7 11.45 7.45 11 8 11H12V2.5Z"/></svg>
          {/if}
          {it.label}
        </button>
      {/each}
    </div>

    <div class="spacer"></div>

    <div class="search">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <circle cx="6" cy="6" r="4.5" stroke="#6b7280" stroke-width="1.4"/>
        <path d="M9.5 9.5L13 13" stroke="#6b7280" stroke-width="1.4" stroke-linecap="round"/>
      </svg>
      <input placeholder="다른 회사 검색 · 005930" />
      <span class="mono kbd">⌘K</span>
    </div>

    <a href="https://buymeacoffee.com/dartlab" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
      <span>☕</span> Buy Me A Coffee
    </a>
  </div>
</nav>

<style>
  .nav {
    position: sticky; top: 0; z-index: 50;
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    background: rgba(5,8,17,0.4);
    border-bottom: 1px solid transparent;
    transition: all .25s;
  }
  .nav.scrolled { background: rgba(5,8,17,0.82); border-bottom-color: var(--border); }
  .nav-inner { display: flex; align-items: center; height: 64px; gap: 24px; }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo-badge {
    width: 34px; height: 34px; border-radius: 9px;
    background: radial-gradient(circle at 30% 25%, #1a1d28, #0a0d14);
    display: grid; place-items: center;
    border: 1px solid var(--border-hi);
    overflow: hidden;
  }
  .logo-badge img { width: 30px; height: 30px; object-fit: contain; }
  .logo-text { display: flex; align-items: baseline; gap: 6px; }
  .brand { font-weight: 800; font-size: 17px; letter-spacing: -0.02em; color: var(--text); }
  .ver { font-size: 10px; color: var(--text-dim); }
  .nav-items { display: flex; gap: 4px; margin-left: 16px; }
  .spacer { flex: 1; }
  .search {
    display: flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.04); border: 1px solid var(--border);
    border-radius: 10px; padding: 7px 12px; width: 260px;
  }
  .search input {
    flex: 1; background: transparent; border: none; outline: none;
    color: var(--text); font-size: 13px; font-family: inherit;
  }
  .kbd {
    font-size: 10px; color: var(--text-faint);
    border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px;
  }
  @media (max-width: 900px) { .nav-items, .search { display: none; } }
</style>
