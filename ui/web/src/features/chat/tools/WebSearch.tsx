// WebSearch — query 강조.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const WebSearchArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.query === 'string') {
		return (
			<div className="text-xs">
				<span className="text-muted-foreground">웹 검색: </span>
				<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{args.query}</code>
			</div>
		);
	}
	return <GenericArgs args={args} />;
};
