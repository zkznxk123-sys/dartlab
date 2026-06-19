import type { PageLoad } from './$types';

// dev 격리 라우트 — 본진 /terminal 무관. 정적 story JSON 직접 fetch.
export const ssr = false;
export const prerender = false;

export const load: PageLoad = async ({ fetch, url }) => {
  const sym = url.searchParams.get('sym') || '005930';
  const reportType = url.searchParams.get('type') || 'full';
  const base = '/story';
  const [manifestRes, reportRes, skipRes] = await Promise.all([
    fetch(`${base}/manifest.json`),
    fetch(`${base}/report-${sym}.json`),
    fetch(`${base}/report-_skipped.json`).catch(() => null)
  ]);
  const manifest = manifestRes.ok ? await manifestRes.json() : null;
  const report = reportRes.ok ? await reportRes.json() : null;
  let skipReason: string | null = null;
  if (!report && skipRes && skipRes.ok) {
    try {
      const skipped: Array<{ code: string; reason: string }> = await skipRes.json();
      skipReason = skipped.find((s) => s.code === sym)?.reason ?? null;
    } catch {
      skipReason = null;
    }
  }
  return { manifest, report, sym, reportType, skipReason };
};
