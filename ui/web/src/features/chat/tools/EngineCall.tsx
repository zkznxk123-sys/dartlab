// EngineCall — apiRef 가 핵심. 별도 강조 + args KV.
import { GenericArgs, KvArgs, isObj, type ArgsRenderer } from './_primitives';

export const EngineCallArgs: ArgsRenderer = ({ args }) => {
	if (!isObj(args)) return <GenericArgs args={args} />;
	const apiRef = typeof args.apiRef === 'string' ? args.apiRef : null;
	const inner = isObj(args.args) ? args.args : null;
	if (!apiRef) return <GenericArgs args={args} />;
	return (
		<div className="space-y-1.5">
			<div className="text-xs">
				<span className="text-muted-foreground">엔진: </span>
				<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{apiRef}</code>
			</div>
			{inner && Object.entries(inner).length > 0 && (
				<KvArgs pairs={Object.entries(inner)} />
			)}
		</div>
	);
};
