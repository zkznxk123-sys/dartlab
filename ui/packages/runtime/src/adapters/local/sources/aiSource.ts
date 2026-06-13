// 로컬 AiPort — 로컬 Python 서버의 AG-UI 게이트웨이(POST /api/agent/runs SSE) 연결.
// capabilities() 는 /api/status 로 provider 구성 여부 probe → 있으면 advanced, 없으면 deterministic(throw 금지·정직 강등).
// streamAsk 는 SSE 를 AiStreamEvent 로 매핑 — 서버 emitter(agentGateway._event)가 data 에 type+계약 필드명을 그대로
// 실어 보내므로(AG-UI allowlist = ai.ts 계약 SSOT) 파싱한 객체를 그대로 통과시킨다.
import type {
	AiAskInput,
	AiAskResult,
	AiCapabilities,
	AiMode,
	AiModeId,
	AiPort,
	AiStreamEvent,
	AiToolRunInput,
	AiToolRunResult,
	EvidenceExplainResult,
	EvidenceRef
} from '@dartlab/ui-contracts';
import { getJson } from '../fetchJson';

interface StatusProbe {
	providers?: Record<string, { available?: boolean | null; secretConfigured?: boolean }>;
}

function buildRequestBody(input: AiAskInput): string {
	return JSON.stringify({
		messages: [{ role: 'user', content: input.prompt }],
		agentId: 'dartlab-research',
		stream: true,
		workspaceContext: input.code ? { stockCode: input.code, mode: input.mode } : { mode: input.mode }
	});
}

// SSE 블록(`event:`/`data:` 라인 묶음) → AiStreamEvent. data JSON 의 type 으로 판별, 계약 필드명 일치라 그대로 통과.
function parseSseBlock(raw: string): AiStreamEvent | null {
	if (!raw.trim()) return null;
	const dataLines: string[] = [];
	for (const line of raw.split('\n')) {
		if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
	}
	const dataStr = dataLines.join('\n');
	if (!dataStr) return null;
	let obj: Record<string, unknown>;
	try {
		obj = JSON.parse(dataStr) as Record<string, unknown>;
	} catch {
		return null;
	}
	if (typeof obj.type !== 'string') return null;
	return obj as unknown as AiStreamEvent;
}

async function* streamAgentRun(apiBase: string, input: AiAskInput): AsyncGenerator<AiStreamEvent> {
	let resp: Response;
	try {
		resp = await fetch(`${apiBase}/api/agent/runs`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
			body: buildRequestBody(input)
		});
	} catch (e) {
		yield { type: 'RUN_ERROR', runId: '', message: String(e), code: 'network_error' };
		return;
	}
	if (!resp.ok || !resp.body) {
		yield { type: 'RUN_ERROR', runId: '', message: `HTTP ${resp.status}`, code: 'http_error' };
		return;
	}
	const reader = resp.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
		let sep = buffer.indexOf('\n\n');
		while (sep !== -1) {
			const block = buffer.slice(0, sep);
			buffer = buffer.slice(sep + 2);
			const ev = parseSseBlock(block);
			if (ev) yield ev;
			sep = buffer.indexOf('\n\n');
		}
	}
}

async function collectAsk(apiBase: string, input: AiAskInput): Promise<AiAskResult> {
	let text = '';
	const refs: EvidenceRef[] = [];
	for await (const ev of streamAgentRun(apiBase, input)) {
		if (ev.type === 'TEXT_MESSAGE_CONTENT') text += ev.delta;
		else if (ev.type === 'TOOL_CALL_RESULT') refs.push(...ev.refDetails);
		else if (ev.type === 'RUN_ERROR') throw new Error(ev.message);
	}
	return { text, refs };
}

export function localAiPort(apiBase: string): AiPort {
	let mode: AiModeId = 'terminal';
	return {
		async capabilities(): Promise<AiCapabilities> {
			const status = await getJson<StatusProbe>(apiBase, '/api/status');
			const providers = status?.providers ?? {};
			const configured = Object.values(providers).some(
				(p) => p?.available === true || p?.secretConfigured === true
			);
			if (configured) {
				return {
					tier: 'advanced',
					streaming: true,
					toolCalling: true,
					localWorkspace: true,
					deterministicAnswers: true,
					providerLabel: 'local'
				};
			}
			// provider 미구성 — 로컬도 결정론 Q&A 이상 동작(throw 금지). 업그레이드 안내만.
			return {
				tier: 'deterministic',
				streaming: true,
				toolCalling: false,
				localWorkspace: true,
				deterministicAnswers: true,
				upgradeHint: '공급자를 설정하면 고급 분석 엔진을 사용할 수 있습니다.'
			};
		},
		ask(input) {
			return collectAsk(apiBase, input);
		},
		streamAsk(input) {
			return streamAgentRun(apiBase, input);
		},
		// 로컬은 단일 도구 직접 실행 엔드포인트 미보유(도구는 streamAsk 내부에서 에이전트가 실행) — honest error(throw 아님).
		async runTool(input: AiToolRunInput): Promise<AiToolRunResult> {
			return {
				status: 'error',
				summary: `단일 도구 직접 실행은 미지원: ${input.toolName}`,
				refs: [],
				error: 'runTool_unsupported'
			};
		},
		async explainEvidence(): Promise<EvidenceExplainResult> {
			return { text: '', refs: [] };
		},
		async listModes(): Promise<AiMode[]> {
			return [
				{ id: 'chat', label: '챗', description: '일반 대화·질의', available: true },
				{ id: 'terminal', label: '터미널', description: '터미널 운영 모드', available: true }
			];
		},
		async setMode(next) {
			mode = next;
		},
		async getMode() {
			return mode;
		}
	};
}
