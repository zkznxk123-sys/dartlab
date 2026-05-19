// 사이드바 회사 검색 input + 결과 리스트.
// 디바운스 200ms · 결과 8 행 · 키보드 ArrowDown/Up/Enter/Esc.

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Search } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { SidebarGroup, SidebarGroupContent, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar';

import { searchCompanies } from '../api/client';
import { dashKeys } from '../api/queryKeys';
import { useDebounce } from '../hooks/useDebounce';
import { usePrefetchCompany } from '../hooks/usePrefetchCompany';
import { useRecentCompanies } from '../hooks/useRecentCompanies';

export function CompanySearch() {
	const navigate = useNavigate();
	const { push } = useRecentCompanies();
	const prefetch = usePrefetchCompany();
	const [q, setQ] = useState('');
	const [focusIdx, setFocusIdx] = useState(-1);
	const dq = useDebounce(q.trim(), 200);
	const inputRef = useRef<HTMLInputElement>(null);

	const { data: hits = [] } = useQuery({
		queryKey: dashKeys.search(dq),
		queryFn: () => searchCompanies(dq, 8),
		enabled: dq.length >= 1,
		staleTime: 60_000,
	});

	useEffect(() => {
		setFocusIdx(hits.length > 0 ? 0 : -1);
	}, [dq, hits.length]);

	// focused row (키보드 cycle / hover) 진입 시 prefetch — 클릭 시점에 이미 캐시 hit.
	useEffect(() => {
		if (focusIdx < 0) return;
		const hit = hits[focusIdx];
		if (hit?.stockCode) prefetch(hit.stockCode);
	}, [focusIdx, hits, prefetch]);

	function pick(idx: number) {
		const hit = hits[idx];
		if (!hit) return;
		push(hit.stockCode, hit.corpName);
		setQ('');
		navigate({ to: '/dashboard/$code', params: { code: hit.stockCode } });
	}

	function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
		if (!hits.length) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			setFocusIdx((i) => (i + 1) % hits.length);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			setFocusIdx((i) => (i - 1 + hits.length) % hits.length);
		} else if (e.key === 'Enter') {
			e.preventDefault();
			pick(focusIdx);
		} else if (e.key === 'Escape') {
			setQ('');
		}
	}

	return (
		<>
			<SidebarGroup className="group-data-[collapsible=icon]:hidden">
				<SidebarGroupContent>
					<div className="relative px-2">
						<Search className="pointer-events-none absolute left-4 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
						<Input
							ref={inputRef}
							value={q}
							onChange={(e) => setQ(e.target.value)}
							onKeyDown={onKey}
							placeholder="회사 검색…"
							className="h-8 pl-7 text-xs"
						/>
					</div>
				</SidebarGroupContent>
			</SidebarGroup>

			{dq.length >= 1 && (
				<SidebarGroup className="group-data-[collapsible=icon]:hidden">
					<SidebarGroupContent>
						<SidebarMenu>
							{hits.length === 0 ? (
								<SidebarMenuItem>
									<div className="px-2 py-1 text-xs text-muted-foreground">검색 결과 없음</div>
								</SidebarMenuItem>
							) : (
								hits.map((h, i) => (
									<SidebarMenuItem key={h.stockCode}>
										<SidebarMenuButton
											isActive={i === focusIdx}
											onClick={() => pick(i)}
											onMouseEnter={() => setFocusIdx(i)}
											tooltip={`${h.corpName} (${h.stockCode})${h.products ? ` — ${h.products}` : ''}`}
											className="h-auto py-1.5"
										>
											<div className="flex w-full min-w-0 flex-col gap-0.5">
												<div className="flex items-baseline gap-2">
													<span className="truncate font-medium">{h.corpName}</span>
													<span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">
														{h.stockCode}
													</span>
												</div>
												{(h.sector || h.products) && (
													<div className="truncate text-[10px] text-muted-foreground">
														{[h.sector, h.products].filter(Boolean).join(' · ')}
													</div>
												)}
											</div>
										</SidebarMenuButton>
									</SidebarMenuItem>
								))
							)}
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>
			)}
		</>
	);
}
