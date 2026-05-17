import { useCallback, useEffect, useState } from 'react';

// localStorage 기반 최근 선택 회사 5 개. SSR 가드 포함.

const KEY = 'dash:recent';
const LIMIT = 5;

export interface RecentCompany {
	stockCode: string;
	corpName: string;
	at: number;
}

function load(): RecentCompany[] {
	if (typeof window === 'undefined') return [];
	try {
		const raw = window.localStorage.getItem(KEY);
		if (!raw) return [];
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return [];
		return parsed.filter((x) => x && typeof x.stockCode === 'string' && typeof x.corpName === 'string');
	} catch {
		return [];
	}
}

function save(items: RecentCompany[]) {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(KEY, JSON.stringify(items));
	} catch {
		/* quota 초과 무시 */
	}
}

export function useRecentCompanies() {
	const [items, setItems] = useState<RecentCompany[]>(() => load());

	useEffect(() => {
		const onStorage = (e: StorageEvent) => {
			if (e.key === KEY) setItems(load());
		};
		window.addEventListener('storage', onStorage);
		return () => window.removeEventListener('storage', onStorage);
	}, []);

	const push = useCallback((stockCode: string, corpName: string) => {
		setItems((prev) => {
			const next = [{ stockCode, corpName, at: Date.now() }, ...prev.filter((x) => x.stockCode !== stockCode)].slice(
				0,
				LIMIT,
			);
			save(next);
			return next;
		});
	}, []);

	const clear = useCallback(() => {
		save([]);
		setItems([]);
	}, []);

	return { items, push, clear };
}
