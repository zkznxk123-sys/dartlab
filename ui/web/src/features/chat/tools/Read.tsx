// Read — 파일 읽기. path 만 강조.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const ReadArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.path === 'string') {
		return (
			<div className="flex items-center gap-2 text-xs">
				<span className="text-muted-foreground">path:</span>
				<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{args.path}</code>
			</div>
		);
	}
	return <GenericArgs args={args} />;
};
