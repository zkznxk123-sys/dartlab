// /analysis 의 기본 화면 — 회사 미선택 시 회사 검색 + 최근 회사 칩.
// ask 모드 EmptyState 와 동일 패턴.

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router';
import { Search } from 'lucide-react';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { searchCompanies } from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { useDebounce } from '@/features/dashboard/hooks/useDebounce';
import { useRecentCompanies } from '@/features/dashboard/hooks/useRecentCompanies';

export const Route = createFileRoute('/analysis/')({
	component: AnalysisIndexPage,
});

function AnalysisIndexPage() {
	const navigate = useNavigate();
	const { items, push } = useRecentCompanies();
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

	function pick(stockCode: string, corpName: string) {
		push(stockCode, corpName);
		setQ('');
		navigate({
			to: '/analysis/$code/financial',
			params: { code: stockCode },
			search: { period: 'quarterly', view: 'snowflake' },
		});
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
			const hit = hits[focusIdx];
			if (hit) pick(hit.stockCode, hit.corpName);
		} else if (e.key === 'Escape') {
			setQ('');
		}
	}

	return (
		<div className="flex flex-1 flex-col items-center justify-center px-4 py-6">
			<div className="w-full max-w-2xl space-y-6">
				<div className="flex flex-col items-center space-y-3 text-center">
					<Avatar className="size-12">
						<AvatarImage src="/avatar.png" alt="DartLab" />
						<AvatarFallback>DL</AvatarFallback>
					</Avatar>
					<h2 className="text-2xl font-semibold tracking-tight">회사를 선택하세요</h2>
					<p className="text-sm text-muted-foreground">
						종목명 또는 종목코드를 입력하면 8 분야 분석 (재무 · 사업포트폴리오 · 가치평가 · 거버넌스 · 동종 · 생애주기 · 거시 · Viewer) 이 한 번에 열립니다.
					</p>
				</div>

				<div className="relative">
					<Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
					<Input
						ref={inputRef}
						value={q}
						onChange={(e) => setQ(e.target.value)}
						onKeyDown={onKey}
						placeholder="회사 검색…"
						className="h-11 pl-9"
						autoFocus
					/>
					{dq.length >= 1 && (
						<div className="absolute left-0 right-0 top-full z-10 mt-1 overflow-hidden rounded-md border bg-popover shadow-md">
							{hits.length === 0 ? (
								<div className="px-3 py-2 text-xs text-muted-foreground">검색 결과 없음</div>
							) : (
								hits.map((h, i) => (
									<button
										key={h.stockCode}
										type="button"
										onClick={() => pick(h.stockCode, h.corpName)}
										onMouseEnter={() => setFocusIdx(i)}
										className={`flex w-full items-center justify-between px-3 py-2 text-sm transition-colors ${
											i === focusIdx ? 'bg-accent text-accent-foreground' : 'hover:bg-accent'
										}`}
									>
										<span className="truncate">{h.corpName}</span>
										<span className="font-mono text-xs text-muted-foreground">{h.stockCode}</span>
									</button>
								))
							)}
						</div>
					)}
				</div>

				{items.length > 0 && (
					<div className="flex flex-wrap justify-center gap-2 pt-2">
						{items.map((r) => (
							<Button key={r.stockCode} variant="outline" size="sm" asChild>
								<Link
									to="/analysis/$code/financial"
									params={{ code: r.stockCode }}
									search={{ period: 'quarterly', view: 'snowflake' }}
									className="text-xs font-normal text-muted-foreground"
								>
									{r.corpName}
									<span className="ml-2 font-mono text-[10px]">{r.stockCode}</span>
								</Link>
							</Button>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
