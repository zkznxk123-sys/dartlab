// SaveArtifact — name + kind 강조, content 는 collapsed preview.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const SaveArtifactArgs: ArgsRenderer = ({ args }) => {
	if (!isObj(args)) return <GenericArgs args={args} />;
	const name = typeof args.name === 'string' ? args.name : null;
	const kind = typeof args.kind === 'string' ? args.kind : null;
	const content = typeof args.content === 'string' ? args.content : null;
	if (!name && !content) return <GenericArgs args={args} />;
	return (
		<div className="space-y-1.5 text-xs">
			<div className="flex items-center gap-2">
				{name && (
					<>
						<span className="text-muted-foreground">파일: </span>
						<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{name}</code>
					</>
				)}
				{kind && (
					<span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase">
						{kind}
					</span>
				)}
			</div>
			{content && (
				<pre className="tiny-scroll max-h-[20vh] overflow-auto rounded-md border border-border bg-muted/20 p-2 whitespace-pre-wrap break-words text-[11px] font-mono">
					{content}
				</pre>
			)}
		</div>
	);
};
