// CompileVisual — chartType 배지 + title + data 행 수 미리보기.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const CompileVisualArgs: ArgsRenderer = ({ args }) => {
	if (!isObj(args)) return <GenericArgs args={args} />;
	const chartType = typeof args.chartType === 'string' ? args.chartType : null;
	const title = typeof args.title === 'string' ? args.title : null;
	const rowCount = Array.isArray(args.data) ? args.data.length : null;
	if (!chartType) return <GenericArgs args={args} />;
	return (
		<div className="space-y-1 text-xs">
			<div className="flex items-center gap-2">
				<span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase">
					{chartType}
				</span>
				{title && <span className="font-medium">{title}</span>}
			</div>
			{rowCount !== null && (
				<div className="text-muted-foreground">행 {rowCount} 개</div>
			)}
		</div>
	);
};
