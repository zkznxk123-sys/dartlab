// 대화 → 마크다운 export 유틸. AppSidebar / 단축키 등에서 호출.
import type { Conversation, Part } from './chat';

function partToMd(p: Part): string {
	if (p.type === 'text') return p.text;
	if (p.type === 'tool') {
		const args = p.args == null ? '' : '\n```json\n' + JSON.stringify(p.args, null, 2) + '\n```';
		const result =
			p.status === 'error'
				? `\n> 실패: ${p.error || ''}`
				: p.result != null
					? '\n```json\n' + JSON.stringify(p.result, null, 2) + '\n```'
					: '';
		return `\n**도구: \`${p.name}\`** ${p.summary ? `· ${p.summary}` : ''}${args}${result}\n`;
	}
	if (p.type === 'viewSpec') {
		return `\n**Artifact: ${p.title || 'view'}**\n\`\`\`json\n${JSON.stringify(p.spec, null, 2)}\n\`\`\`\n`;
	}
	return '';
}

export function conversationToMarkdown(c: Conversation): string {
	const head = `# ${c.title || '새 대화'}\n\n_생성: ${new Date(c.createdAt).toLocaleString('ko-KR')}_\n\n---\n`;
	const body = c.messages
		.map((m) => {
			const who = m.role === 'user' ? '🧑 사용자' : '🤖 DartLab';
			const content = m.parts.map(partToMd).join('').trim();
			return `## ${who}\n\n${content}\n`;
		})
		.join('\n');
	return head + '\n' + body;
}

export function downloadMarkdown(c: Conversation) {
	const md = conversationToMarkdown(c);
	const safeName = (c.title || 'dartlab-conversation').replace(/[\\/:*?"<>|]/g, '_');
	const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `${safeName}.md`;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}
