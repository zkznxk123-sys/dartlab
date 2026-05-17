// 도구별 args 렌더러 registry — 신규 도구 추가 시: 본 파일에 import + map 한 줄.
// 결과는 ResultBody (results/ResultBody.tsx) 가 모양 dispatch 로 처리하므로 args 만 다룬다.
import { CompileVisualArgs } from './CompileVisual';
import { EngineCallArgs } from './EngineCall';
import { GetSkillBodyArgs } from './GetSkillBody';
import { InspectDatasetArgs } from './InspectDataset';
import { ReadArgs } from './Read';
import { ReadSkillArgs } from './ReadSkill';
import { RunPythonArgs } from './RunPython';
import { RunShellArgs } from './RunShell';
import { SaveArtifactArgs } from './SaveArtifact';
import { WebSearchArgs } from './WebSearch';
import { GenericArgs, type ArgsRenderer } from './_primitives';

const renderers: Record<string, ArgsRenderer> = {
	// 분석 절차 / 메타
	ReadSkill: ReadSkillArgs,
	ReadCapability: ReadSkillArgs, // 같은 양식
	ReadSkillMarket: ReadSkillArgs,
	GetSkillBody: GetSkillBodyArgs,
	// 데이터 호출 / 실행
	EngineCall: EngineCallArgs,
	RunPython: RunPythonArgs,
	RunShell: RunShellArgs,
	InspectDataset: InspectDatasetArgs,
	// 파일 / 외부
	Read: ReadArgs,
	WebSearch: WebSearchArgs,
	// 산출
	SaveArtifact: SaveArtifactArgs,
	CompileVisual: CompileVisualArgs,
};

export function ToolArgs({ name, args }: { name: string; args: unknown }) {
	const R = renderers[name] ?? GenericArgs;
	return <R args={args} />;
}
