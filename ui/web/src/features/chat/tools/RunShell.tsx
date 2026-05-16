// RunShell — args.command 를 bash 코드블록 양식.
import { CodeArgs, GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const RunShellArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.command === 'string') {
		return <CodeArgs code={args.command} lang="bash" />;
	}
	return <GenericArgs args={args} />;
};
