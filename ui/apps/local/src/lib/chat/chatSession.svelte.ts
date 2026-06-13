// 로컬 챗 모드 세션 상태 — AiPort.streamAsk(mode:'chat') 한 포트로 대화·스트리밍·근거를 누적한다.
// surface 가 아니라 로컬 셸 전용 UI 상태(runes)다. 터미널 모드와 같은 Ask engine 계약(AiPort)을 공유 —
// 02 §4 / 단계-7 "챗모드와 터미널모드가 같은 Ask engine contract 사용".
//
// Svelte 5 주의: $state 배열에 push 한 객체는 인덱스 접근(this.messages[i])으로만 reactive proxy 다 —
// push 직전 로컬 참조를 직접 변형하면 비반응. 모든 변형은 활성 인덱스(this.messages[idx])로 한다.
import type {
	AiCapabilities,
	AiPort,
	AiStreamEvent,
	EvidenceRef
} from '@dartlab/ui-contracts';

export interface ChatActivity {
	id: string;
	summary: string;
	status: 'running' | 'done';
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	text: string;
	refs: EvidenceRef[];
	activities: ChatActivity[];
	suggested: string[];
	error: string | null;
	streaming: boolean;
}

export class ChatSession {
	messages = $state<ChatMessage[]>([]);
	capabilities = $state<AiCapabilities | null>(null);
	capabilitiesLoaded = $state(false);
	busy = $state(false);
	/** 선택적 회사 컨텍스트 — 6자리면 streamAsk 에 code 로 전달(터미널과 동일 종목 스코프). */
	code = $state('');

	#ai: AiPort;
	#seq = 0;

	constructor(ai: AiPort) {
		this.#ai = ai;
	}

	async loadCapabilities(): Promise<void> {
		try {
			this.capabilities = await this.#ai.capabilities();
		} catch {
			this.capabilities = null;
		} finally {
			this.capabilitiesLoaded = true;
		}
	}

	#nextId(prefix: string): string {
		this.#seq += 1;
		return `${prefix}-${this.#seq}`;
	}

	async send(prompt: string): Promise<void> {
		const text = prompt.trim();
		if (!text || this.busy) return;
		this.busy = true;

		this.messages.push({
			id: this.#nextId('u'),
			role: 'user',
			text,
			refs: [],
			activities: [],
			suggested: [],
			error: null,
			streaming: false
		});
		this.messages.push({
			id: this.#nextId('a'),
			role: 'assistant',
			text: '',
			refs: [],
			activities: [],
			suggested: [],
			error: null,
			streaming: true
		});
		const idx = this.messages.length - 1;

		const code = this.code.trim();
		try {
			for await (const ev of this.#ai.streamAsk({
				prompt: text,
				mode: 'chat',
				code: /^\d{6}$/.test(code) ? code : undefined
			})) {
				this.#apply(idx, ev);
			}
		} catch (e) {
			this.messages[idx].error = e instanceof Error ? e.message : String(e);
		} finally {
			this.messages[idx].streaming = false;
			this.busy = false;
		}
	}

	#apply(idx: number, ev: AiStreamEvent): void {
		const m = this.messages[idx];
		switch (ev.type) {
			case 'TEXT_MESSAGE_CONTENT':
				m.text += ev.delta;
				break;
			case 'TOOL_CALL_START':
				m.activities.push({ id: ev.toolCallId, summary: ev.toolName, status: 'running' });
				break;
			case 'TOOL_CALL_RESULT': {
				const a = m.activities.find((x) => x.id === ev.toolCallId);
				if (a) {
					a.status = 'done';
					if (ev.summary) a.summary = ev.summary;
				}
				if (ev.refDetails?.length) m.refs.push(...ev.refDetails);
				break;
			}
			case 'ACTIVITY_DELTA':
				m.activities.push({ id: this.#nextId('act'), summary: ev.summary, status: ev.status });
				break;
			case 'RUN_FINISHED':
				m.suggested = ev.suggestedQuestions ?? [];
				break;
			case 'RUN_ERROR':
				m.error = ev.message;
				break;
			// 기타 allowlist 이벤트(START/END/SNAPSHOT/VIEW_SPEC 등)는 챗 렌더 무관 — 드롭.
		}
	}

	reset(): void {
		this.messages = [];
	}
}
