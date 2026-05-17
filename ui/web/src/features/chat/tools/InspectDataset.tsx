// InspectDataset — target + sampleRows.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const InspectDatasetArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.target === 'string') {
		return (
			<div className="space-y-1 text-xs">
				<div>
					<span className="text-muted-foreground">대상: </span>
					<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{args.target}</code>
				</div>
				{typeof args.sampleRows === 'number' && (
					<div className="text-muted-foreground">샘플 {args.sampleRows} 행</div>
				)}
			</div>
		);
	}
	return <GenericArgs args={args} />;
};
