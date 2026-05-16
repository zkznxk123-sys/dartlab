// RunPython — args.code 를 python 코드블록 양식.
import { CodeArgs, GenericArgs, isObj, type ArgsRenderer } from './_primitives';

export const RunPythonArgs: ArgsRenderer = ({ args }) => {
	if (isObj(args) && typeof args.code === 'string') {
		return <CodeArgs code={args.code} lang="python" />;
	}
	return <GenericArgs args={args} />;
};
