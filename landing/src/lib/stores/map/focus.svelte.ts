/**
 * Focus 스토어 — 선택 상태 + 비교 슬롯 관리.
 *
 * 책임 분리:
 * - selectedNode / selectedDetail / selectedDetailLoading
 * - compareSet (최대 4사) + legacy compareB 2-way
 * - loadCompanyDetail(stockCode) — fetch + 캐시
 *
 * UI 라우팅 상태(viewMode, drillIndustry)는 별도 스토어에서. 여기는 "회사 선택"만.
 */

import { base } from '$app/paths';

export interface CompanyDetail {
	ego?: any;
	aiInsight?: any;
	blogPosts?: any[];
	financials5y?: any[];
	supplyInsights?: any;
	suppliers?: any[];
	customers?: any[];
	peers?: any[];
	[k: string]: any;
}

export interface CompareItem {
	node: any;
	detail: CompanyDetail | null;
}

export const COMPARE_MAX = 4;

class FocusStore {
	selected = $state<any>(null);
	detail = $state<CompanyDetail | null>(null);
	detailLoading = $state(false);
	detailCode = $state<string | null>(null);
	compareSet = $state<CompareItem[]>([]);

	// 레거시: /map 우측 패널 2-way
	compareB = $state<any>(null);
	compareBDetail = $state<CompanyDetail | null>(null);

	private detailCache = new Map<string, CompanyDetail>();

	get comparing(): boolean {
		return !!this.compareB;
	}

	async loadDetail(stockCode: string): Promise<CompanyDetail | null> {
		if (!stockCode) return null;
		if (this.detailCache.has(stockCode)) {
			return this.detailCache.get(stockCode) || null;
		}
		try {
			const r = await fetch(`${base}/map/companies/${stockCode}.json`);
			if (!r.ok) return null;
			const d = await r.json();
			this.detailCache.set(stockCode, d);
			return d;
		} catch {
			return null;
		}
	}

	async select(node: any) {
		if (!node) {
			this.selected = null;
			this.detail = null;
			this.detailCode = null;
			return;
		}
		this.selected = node;
		if (this.detailCode === node.id && this.detail) return;
		this.detailLoading = true;
		this.detailCode = node.id;
		try {
			this.detail = await this.loadDetail(node.id);
		} finally {
			this.detailLoading = false;
		}
	}

	async addCompare(stockCode: string, nodeLookup: (id: string) => any): Promise<boolean> {
		if (!stockCode) return false;
		if (this.compareSet.find((x) => x.node?.id === stockCode)) return false;
		if (this.compareSet.length >= COMPARE_MAX) return false;
		const node = nodeLookup(stockCode);
		if (!node) return false;
		const detail = await this.loadDetail(stockCode);
		this.compareSet = [...this.compareSet, { node, detail }];

		// 레거시 compareB — compareSet 의 두 번째 회사
		if (this.compareSet.length >= 2 && this.selected) {
			const other = this.compareSet.find((x) => x.node?.id !== this.selected.id);
			if (other) {
				this.compareB = other.node;
				this.compareBDetail = other.detail;
			}
		}
		return true;
	}

	removeCompare(stockCode: string) {
		this.compareSet = this.compareSet.filter((x) => x.node?.id !== stockCode);
		if (this.compareB?.id === stockCode) {
			this.compareB = null;
			this.compareBDetail = null;
		}
	}

	clearCompare() {
		this.compareSet = [];
		this.compareB = null;
		this.compareBDetail = null;
	}

	clearAll() {
		this.selected = null;
		this.detail = null;
		this.detailCode = null;
		this.compareSet = [];
		this.compareB = null;
		this.compareBDetail = null;
	}
}

export const focus = new FocusStore();
