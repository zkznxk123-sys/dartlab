import { Loader2, Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

import { searchViewerIndex, type ViewerSearchHit, type ViewerSearchIndex } from './searchIndex';

interface Props {
	index: ViewerSearchIndex | null;
	indexing: boolean;
	onEnsureIndex: () => void;
	onPick: (hit: ViewerSearchHit) => void;
}

export function ViewerCommandPalette({ index, indexing, onEnsureIndex, onPick }: Props) {
	const [open, setOpen] = useState(false);
	const [query, setQuery] = useState('');

	const result = useMemo(() => {
		if (!index || !query.trim()) return { hits: [], added: [] };
		return searchViewerIndex(index, query.trim(), 10);
	}, [index, query]);

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				setOpen(next);
				if (next && !index && !indexing) onEnsureIndex();
			}}
		>
			<DialogTrigger asChild>
				<Button type="button" variant="outline" size="sm" className="h-8 gap-1.5">
					<Search className="size-3.5" />
					검색
				</Button>
			</DialogTrigger>
			<DialogContent className="max-w-2xl p-0">
				<DialogHeader className="border-b px-4 py-3">
					<DialogTitle className="text-sm">공시 본문 깊은 검색</DialogTitle>
					<DialogDescription className="sr-only">
						현재 회사의 공시 본문 색인에서 항목, 금액, 키워드를 검색합니다.
					</DialogDescription>
				</DialogHeader>
				<div className="p-4">
					<div className="relative">
						<Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
						<Input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder="예: 소송, 100억 이상, 자사주, 특수관계자"
							className="h-10 pl-9"
							autoFocus
						/>
					</div>
					<div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
						{indexing ? (
							<>
								<Loader2 className="size-3 animate-spin" />
								<span>전체 공시 색인 생성 중</span>
							</>
						) : index ? (
							<span>
								행 {index.rows.length.toLocaleString('ko-KR')} · 어휘 {index.vocab.toLocaleString('ko-KR')}
							</span>
						) : (
							<Button type="button" size="sm" variant="secondary" onClick={onEnsureIndex}>
								색인 준비
							</Button>
						)}
						{result.added.length > 0 && (
							<div className="flex min-w-0 flex-wrap gap-1">
								{result.added.slice(0, 5).map((term) => (
									<Badge key={term} variant="outline" className="px-1 py-0 text-[10px]">
										{term}
									</Badge>
								))}
							</div>
						)}
					</div>
					<div className="mt-3 max-h-[420px] overflow-y-auto tiny-scroll">
						{query.trim() && index && result.hits.length === 0 && (
							<div className="py-10 text-center text-sm text-muted-foreground">검색 결과 없음</div>
						)}
						{result.hits.map((hit, idx) => (
							<button
								key={`${hit.sectionKey}-${hit.rowIndex}-${hit.period}`}
								type="button"
								onClick={() => {
									onPick(hit);
									setOpen(false);
								}}
								className="block w-full border-b px-1 py-3 text-left hover:bg-accent/40"
							>
								<div className="flex items-center justify-between gap-3">
									<div className="min-w-0 truncate text-sm font-medium">
										{idx + 1}. {hit.section}
										{hit.block ? ` · ${hit.block}` : ''}
									</div>
									<div className="flex shrink-0 items-center gap-1">
										<Badge variant={hit.matchKind === 'amount' ? 'default' : 'secondary'} className="px-1.5 py-0 text-[10px]">
											{hit.period}
										</Badge>
										{hit.stale && (
											<Badge variant="outline" className="px-1.5 py-0 text-[10px]">
												과거
											</Badge>
										)}
									</div>
								</div>
								<div className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
									{hit.snippet || `${hit.chapter} / ${hit.section}`}
								</div>
							</button>
						))}
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
