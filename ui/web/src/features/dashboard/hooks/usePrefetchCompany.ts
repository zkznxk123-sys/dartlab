// 회사 페이지 진입 직전 prefetch — hover/focus 시 또는 허브 마운트 시 호출.
// 두 모드 (financial / viewer) 모두 준비하되 우선순위는 lastMode 기준.
//
// 큐 모델:
//   - module-level singleton idle queue, concurrency 2.
//   - requestIdleCallback fallback setTimeout 0 — 메인 thread paint 양보.
//   - hover prefetch 폭주에도 race·중복은 backend viz._prefetchCompany dedup +
//     spec TTL 캐시가 차단. queue 는 *클라이언트 측 동시 호출 폭* 만 제어.
//
// 우선순위:
//   - 사용자가 직전에 본 모드를 먼저 enqueue (재진입 확률 높음).
//   - 둘 다 받지만 직전 모드가 항상 head 가까이.

import { useQueryClient } from '@tanstack/react-query';

import { fetchCompanyMeta, fetchTabLayout, type PeriodKind } from '../api/client';
import { dashKeys } from '../api/queryKeys';
import { useDashboardMode, type DashboardMode } from '../store/dashboardMode';

type Task = () => Promise<unknown>;

class IdleQueue {
	private queue: Task[] = [];
	private running = 0;
	private readonly concurrency: number;

	constructor(concurrency: number) {
		this.concurrency = concurrency;
	}

	enqueue(task: Task): void {
		this.queue.push(task);
		this.tick();
	}

	private tick(): void {
		while (this.running < this.concurrency && this.queue.length > 0) {
			const task = this.queue.shift()!;
			this.running += 1;
			this.scheduleIdle(() => {
				task()
					.catch(() => undefined)
					.finally(() => {
						this.running -= 1;
						this.tick();
					});
			});
		}
	}

	private scheduleIdle(fn: () => void): void {
		if (typeof window === 'undefined') {
			fn();
			return;
		}
		const w = window as unknown as {
			requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => void;
		};
		if (typeof w.requestIdleCallback === 'function') {
			w.requestIdleCallback(fn, { timeout: 800 });
		} else {
			setTimeout(fn, 0);
		}
	}
}

const idleQueue = new IdleQueue(2);

interface ViewerInitResponse {
	stockCode: string;
	corpName: string;
	toc: unknown;
	firstTopic: string | null;
	firstChapter: string | null;
	viewer: unknown;
}

function viewerInitKey(stockCode: string) {
	return ['viewer', 'init', stockCode] as const;
}

export interface PrefetchOptions {
	periodKind?: PeriodKind;
	// 'auto' = useDashboardMode 의 lastMode 사용. 명시값은 우선.
	priority?: DashboardMode | 'auto';
	// 두 모드 모두 prefetch (허브 / 라우터 진입 직전). false = meta 만 (가벼운 hover).
	full?: boolean;
}

export function usePrefetchCompany() {
	const queryClient = useQueryClient();
	const lastMode = useDashboardMode((s) => s.lastMode);
	return (stockCode: string, opts: PrefetchOptions = {}) => {
		if (!stockCode) return;
		const periodKind: PeriodKind = opts.periodKind ?? 'quarterly';
		const full = opts.full ?? false;
		const requested = opts.priority ?? 'auto';
		const priority: DashboardMode = requested === 'auto' ? lastMode ?? 'financial' : requested;

		// meta 는 즉시 — corpName 표시에 필요. 비용 0~5ms (kindlist 룩업).
		void queryClient.prefetchQuery({
			queryKey: dashKeys.companyMeta(stockCode),
			queryFn: () => fetchCompanyMeta(stockCode),
			staleTime: 10 * 60_000,
		});

		if (!full) {
			// hover prefetch — 우선순위 모드만 idle queue 에. 다른 모드는 허브 진입 시.
			const task =
				priority === 'viewer'
					? () =>
							queryClient.prefetchQuery({
								queryKey: viewerInitKey(stockCode),
								queryFn: async () => {
									const r = await fetch(`/api/company/${stockCode}/init?compact=true&limit=60`);
									if (!r.ok) throw new Error(`HTTP ${r.status}`);
									return (await r.json()) as ViewerInitResponse;
								},
								staleTime: 5 * 60_000,
							})
					: () =>
							queryClient.prefetchQuery({
								queryKey: dashKeys.tabLayout('financial', stockCode, null, periodKind),
								queryFn: () => fetchTabLayout('financial', stockCode, null, periodKind, 40, false, 40),
								staleTime: 5 * 60_000,
							});
			idleQueue.enqueue(task);
			return;
		}

		// full prefetch — 두 모드 모두. 우선순위 모드 먼저 enqueue.
		const financialTask: Task = () =>
			queryClient.prefetchQuery({
				queryKey: dashKeys.tabLayout('financial', stockCode, null, periodKind),
				queryFn: () => fetchTabLayout('financial', stockCode, null, periodKind, 40, false, 40),
				staleTime: 5 * 60_000,
			});
		const viewerTask: Task = () =>
			queryClient.prefetchQuery({
				queryKey: viewerInitKey(stockCode),
				queryFn: async () => {
					const r = await fetch(`/api/company/${stockCode}/init?compact=true&limit=60`);
					if (!r.ok) throw new Error(`HTTP ${r.status}`);
					return (await r.json()) as ViewerInitResponse;
				},
				staleTime: 5 * 60_000,
			});

		if (priority === 'viewer') {
			idleQueue.enqueue(viewerTask);
			idleQueue.enqueue(financialTask);
		} else {
			idleQueue.enqueue(financialTask);
			idleQueue.enqueue(viewerTask);
		}
	};
}
