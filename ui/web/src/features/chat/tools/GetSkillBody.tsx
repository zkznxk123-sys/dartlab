// GetSkillBody — skillId 한 개.
import { GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const GetSkillBodyArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.skillId === 'string') {
		return (
			<div className="text-xs">
				<span className="text-muted-foreground">skill: </span>
				<code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono">{args.skillId}</code>
			</div>
		);
	}
	return <GenericArgs args={args} />;
};
