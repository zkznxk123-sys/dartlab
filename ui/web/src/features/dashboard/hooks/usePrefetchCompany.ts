// 회사 페이지 진입 직전 (검색 결과 hover / focus, 최근 회사 hover, 회사 카드 hover)
// 에 companyMeta + financial + quant tab layout 을 미리 fetch → 클릭 시점에 이미 캐시 hit.
// 인지 latency 0. 백엔드 prefetch dedup (viz._prefetchCompany) + spec TTL 캐시
// 가 이미 박혀있어 hover 폭주에도 race·중복 비용 0.
//
// layoutOnly=true 로 layout 만 가져옴 — 카드 spec 은 frontend IntersectionObserver
// 가 viewport 진입 시 lazy fetch. prefetch cost 가벼움 (~수 KB).

import { useQueryClient } from '@tanstack/react-query';

import { fetchCompanyMeta, fetchTabLayout, type PeriodKind } from '../api/client';
import { dashKeys } from '../api/queryKeys';

export function usePrefetchCompany() {
	const queryClient = useQueryClient();
	return (stockCode: string, periodKind: PeriodKind = 'quarterly') => {
		if (!stockCode) return;
		void queryClient.prefetchQuery({
			queryKey: dashKeys.companyMeta(stockCode),
			queryFn: () => fetchCompanyMeta(stockCode),
			staleTime: 10 * 60_000,
		});
		void queryClient.prefetchQuery({
			queryKey: dashKeys.tabLayout('financial', stockCode, null, periodKind),
			queryFn: () => fetchTabLayout('financial', stockCode, null, periodKind, 40, false),
			staleTime: 5 * 60_000,
		});
		void queryClient.prefetchQuery({
			queryKey: dashKeys.tabLayout('quant', stockCode, null, periodKind),
			queryFn: () => fetchTabLayout('quant', stockCode, null, periodKind, 40, true),
			staleTime: 5 * 60_000,
		});
	};
}
