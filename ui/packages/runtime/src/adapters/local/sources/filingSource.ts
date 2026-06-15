// 로컬 filing 포트 — /api/company/{code}/panel/{init,toc} + /panel?section + price-events 이벤트.
// ui/web 브리지의 순수 정규화기(tocToContract/gridToContract/initToContract/regularFilingsFromPanel/
// nonRegularFromEvents) 를 verbatim 포팅 — React 클라이언트 fetch 만 getJson 으로 치환.
import type {
	FilingPort,
	NonRegularFiling,
	PanelGridResponse,
	PanelInitResponse,
	PanelTocResponse,
	RegularFiling
} from '@dartlab/ui-contracts';
import { getJson } from '../fetchJson';
import type {
	ClientPanelGrid,
	ClientPanelInit,
	ClientPanelToc,
	LocalCaches,
	PriceEventsPayload
} from '../localTypes';
import { loadPriceEvents } from './priceSource';

// 로컬 panel toc 는 leafType/disclosureKey 메타 미탑재 — 미제공 = null 정직 표기 (위조 금지).
function tocToContract(toc: ClientPanelToc): PanelTocResponse {
	return {
		stockCode: toc.stockCode,
		corpName: toc.corpName,
		periods: toc.periods,
		chapters: toc.chapters.map((ch) => ({
			chapter: ch.chapter,
			sections: ch.sections.map((s) => ({
				sectionLeaf: s.sectionLeaf,
				sectionKey: s.sectionKey,
				blocks: s.blocks.map((b) => ({ blockLeaf: b.blockLeaf, leafType: null, disclosureKey: null }))
			}))
		}))
	};
}

// chapter/sectionLeaf 가 null 이면 sectionKey(`${chapter}␟${sectionLeaf}`)에서 파생 — 키가 SSOT.
function gridToContract(g: ClientPanelGrid): PanelGridResponse {
	const [keyChapter = '', keyLeaf = ''] = g.sectionKey.split('␟');
	const dartUrlByPeriod = g.dartUrlByPeriod
		? Object.fromEntries(
				Object.entries(g.dartUrlByPeriod).filter((e): e is [string, string] => e[1] != null)
			)
		: undefined;
	return {
		stockCode: g.stockCode,
		corpName: g.corpName,
		chapter: g.chapter ?? keyChapter,
		sectionLeaf: g.sectionLeaf ?? keyLeaf,
		sectionKey: g.sectionKey,
		periods: g.periods,
		rows: g.rows.map((r) => ({ ...r, leafType: null })),
		dartUrlByPeriod
	};
}

// init 필수 구성(grid·first 포인터) 결손 = 사용 가능한 패널 없음 → null 정직 표기.
function initToContract(init: ClientPanelInit | null): PanelInitResponse | null {
	if (!init || !init.grid || init.firstChapter == null || init.firstSectionKey == null) return null;
	return {
		stockCode: init.stockCode,
		corpName: init.corpName,
		toc: tocToContract(init.toc),
		firstChapter: init.firstChapter,
		firstSectionKey: init.firstSectionKey,
		grid: gridToContract(init.grid)
	};
}

function rceptNoFromUrl(url: string | null | undefined): string {
	if (!url) return '';
	const m = url.match(/rcpNo=(\d{8,})/) ?? url.match(/(\d{14})/);
	return m?.[1] ?? '';
}

function rceptDateFromNo(rceptNo: string): string {
	const s = rceptNo.slice(0, 8);
	return /^\d{8}$/.test(s) ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : '';
}

function reportTypeFromPeriod(period: string): string {
	const key = period.toUpperCase();
	if (key.endsWith('Q4')) return '사업보고서';
	if (key.endsWith('Q2')) return '반기보고서';
	if (key.endsWith('Q1') || key.endsWith('Q3')) return '분기보고서';
	return '정기보고서';
}

function regularFilingsFromPanel(panel: ClientPanelInit | null): RegularFiling[] {
	const periods = panel?.toc.periods ?? [];
	const urlByPeriod = panel?.grid?.dartUrlByPeriod ?? {};
	return periods.flatMap((period) => {
		const url = urlByPeriod[period];
		const rceptNo = rceptNoFromUrl(url);
		if (!rceptNo) return [];
		return [
			{
				rceptNo,
				rceptDate: rceptDateFromNo(rceptNo),
				reportType: reportTypeFromPeriod(period),
				year: period.slice(0, 4),
				url: url ?? `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${rceptNo}`
			}
		];
	});
}

function nonRegularFromEvents(payload: PriceEventsPayload | null): NonRegularFiling[] {
	const out: NonRegularFiling[] = [];
	for (const [date, events] of Object.entries(payload?.events ?? {})) {
		for (const d of events.disclosures ?? []) {
			if (['사업보고서', '반기보고서', '분기보고서'].some((name) => d.title.includes(name))) continue;
			out.push({ rceptNo: d.rceptNo, rceptDate: date, reportNm: d.title, filer: payload?.corpName ?? '', url: d.url });
		}
	}
	return out.sort((a, b) => b.rceptDate.localeCompare(a.rceptDate)); // 캡 없음 — price-events 커버리지만큼 전부(딥 심화는 백엔드 후속)
}

function loadPanelInit(apiBase: string, caches: LocalCaches, code: string): Promise<ClientPanelInit | null> {
	const c = code.trim();
	let p = caches.panelInit.get(c);
	if (!p) {
		p = getJson<ClientPanelInit>(apiBase, `/api/company/${encodeURIComponent(c)}/panel/init`);
		caches.panelInit.set(c, p);
	}
	return p;
}

export function localFilingPort(apiBase: string, caches: LocalCaches): FilingPort {
	return {
		async regular(code, limit = 500) {
			return regularFilingsFromPanel(await loadPanelInit(apiBase, caches, code)).slice(0, limit);
		},
		async nonRegular(code) {
			return nonRegularFromEvents(await loadPriceEvents(apiBase, caches, code));
		},
		async panelToc(code) {
			const toc = await getJson<ClientPanelToc>(
				apiBase,
				`/api/company/${encodeURIComponent(code.trim())}/panel/toc`
			);
			return toc ? tocToContract(toc) : null;
		},
		async panelInit(code) {
			return initToContract(await loadPanelInit(apiBase, caches, code));
		},
		async panelGrid(code, sectionKey) {
			const qs = new URLSearchParams({ section: sectionKey });
			const grid = await getJson<ClientPanelGrid>(
				apiBase,
				`/api/company/${encodeURIComponent(code.trim())}/panel?${qs.toString()}`
			);
			return grid ? gridToContract(grid) : null;
		}
	};
}
