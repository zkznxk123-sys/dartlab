// ReadSkill / ReadCapability — "검색: {query}" + 부가 인자.
import { GenericArgs, KvArgs, isObj, type ArgsRenderer } from './_primitives';

export const ReadSkillArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args)) {
		const q = args.query;
		if (typeof q === 'string' && q) {
			const rest = Object.entries(args).filter(([k]) => k !== 'query');
			return (
				<div className="space-y-1">
					<div className="text-xs">
						<span className="text-muted-foreground">검색: </span>
						<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{q}</code>
					</div>
					{rest.length > 0 && <KvArgs pairs={rest} />}
				</div>
			);
		}
	}
	return <GenericArgs args={args} />;
};
