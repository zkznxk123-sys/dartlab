// kind=comparisonTable — peer / sector 백분위 비교 표.
// 회사 vs 산업 평균 row 별 percentile 색 띠.

import { cn } from '@/lib/utils';
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table';

export interface ComparisonRow {
	metric: string;          // 지표명
	value: number | null;    // 회사 값
	peer?: number | null;    // 동종 평균 (선택)
	percentile?: number | null;  // 0~100, 회사 위치
	unit?: string;
}

interface Props {
	rows: ComparisonRow[];
	companyLabel?: string;
}

function tone(pct: number | null | undefined): string {
	if (pct == null) return 'text-muted-foreground';
	if (pct >= 75) return 'text-[var(--chart-5)]';        // 상위
	if (pct >= 50) return 'text-foreground';
	if (pct >= 25) return 'text-[var(--chart-2)]';        // 중하위
	return 'text-[var(--chart-3)]';                        // 하위
}

function fmt(v: number | null | undefined, unit?: string): string {
	if (v == null || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(1) + '%';
	if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0) + '억';
	if (Math.abs(v) >= 1000) return v.toLocaleString();
	return v.toFixed(2);
}

export function ComparisonTable({ rows, companyLabel = '회사' }: Props) {
	return (
		<div className="flex h-full w-full flex-col justify-start overflow-auto px-2">
			<Table className="h-full">
				<TableHeader>
					<TableRow>
						<TableHead>지표</TableHead>
						<TableHead className="text-right">{companyLabel}</TableHead>
						<TableHead className="text-right">동종 평균</TableHead>
						<TableHead className="text-right">백분위</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{rows.map((r) => (
						<TableRow key={r.metric}>
							<TableCell className="font-medium">{r.metric}</TableCell>
							<TableCell className={cn('text-right tabular-nums', tone(r.percentile))}>{fmt(r.value, r.unit)}</TableCell>
							<TableCell className="text-right text-muted-foreground tabular-nums">{fmt(r.peer, r.unit)}</TableCell>
							<TableCell className="text-right">
								{r.percentile != null ? (
									<div className="flex items-center justify-end gap-2">
										<div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
											<div
												className="h-full bg-foreground/60"
												style={{ width: `${Math.max(0, Math.min(100, r.percentile))}%` }}
											/>
										</div>
										<span className="font-mono text-xs text-muted-foreground">{r.percentile.toFixed(0)}</span>
									</div>
								) : (
									<span className="text-muted-foreground">–</span>
								)}
							</TableCell>
						</TableRow>
					))}
				</TableBody>
			</Table>
		</div>
	);
}
