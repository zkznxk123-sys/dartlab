// DartLab Terminal — 공유 UI 헬퍼 (bilingual 해석 · tone 클래스 · 포맷).
import type { Bilingual, Lang, Tone } from '../data/types';

type MaybeBilingual = Bilingual | { kr?: string; en?: string } | string | null | undefined;

export function tx(obj: MaybeBilingual, lang: Lang): string {
	if (obj == null) return '';
	if (typeof obj === 'string') return obj;
	if (lang === 'dual') return (obj.kr || '') + (obj.en && obj.en !== obj.kr ? ' · ' + obj.en : '');
	return obj[lang] || obj.kr || obj.en || '';
}
// compact: dual 은 KR 로 collapse (dense 라벨용)
export function txc(obj: MaybeBilingual, lang: Lang): string {
	if (obj == null) return '';
	if (typeof obj === 'string') return obj;
	return lang === 'en' ? obj.en || obj.kr || '' : obj.kr || obj.en || '';
}

export function toneClass(t: Tone | string | undefined): string {
	return (
		{ up: 'tUp', down: 'tDn', good: 'tGood', warn: 'tWarn', neutral: 'tNeu' } as Record<string, string>
	)[t || 'neutral'] || 'tNeu';
}
export function chgClass(n: number | null | undefined): string {
	return n != null && n > 0 ? 'tUp' : n != null && n < 0 ? 'tDn' : 'tNeu';
}

export function fmtNum(n: number | null | undefined, d = 0): string {
	if (n == null || Number.isNaN(n)) return '—';
	return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
export function fmtAbbr(n: number | null | undefined): string {
	if (n == null || Number.isNaN(n)) return '—';
	const a = Math.abs(n);
	if (a >= 1e12) return (n / 1e12).toFixed(2) + 'T';
	if (a >= 1e9) return (n / 1e9).toFixed(2) + 'B';
	if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M';
	if (a >= 1e3) return (n / 1e3).toFixed(0) + 'K';
	return '' + n;
}
export function sign(n: number | null | undefined, d = 2): string {
	if (n == null || Number.isNaN(n)) return '—';
	return (n > 0 ? '+' : '') + fmtNum(n, d);
}
// heat color for sector/change cells (한국 컨벤션: 상승=빨강, 하락=파랑)
export function heat(v: number, max = 1): string {
	const t = Math.max(-1, Math.min(1, v / max));
	if (t >= 0) return `rgba(228, 63, 63, ${0.06 + t * 0.45})`;
	return `rgba(29, 100, 220, ${0.06 + -t * 0.45})`;
}

export const PROV: Record<string, { kr: string; en: string; cls: string; t: Bilingual }> = {
	live: { kr: 'LIVE', en: 'LIVE', cls: 'pLive', t: { kr: 'HuggingFace 실데이터', en: 'real HF data' } },
	derived: { kr: '파생', en: 'DERIVED', cls: 'pDeriv', t: { kr: '실데이터에서 계산 (엔진출력 아님)', en: 'computed from real data' } },
	wire: { kr: '재구성', en: 'RECON', cls: 'pWire', t: { kr: '실 지표 기반 재구성', en: 'reconstructed from real metrics' } }
};
