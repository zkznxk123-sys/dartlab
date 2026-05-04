import { useCallback, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  Circle,
  Code2,
  FileText,
  Menu,
  PanelRight,
  Plus,
  Search,
  Send,
  Settings2,
  Sparkles,
  SquareTerminal,
} from 'lucide-react';

const INITIAL_SUGGESTIONS = ['삼성전자 재무상태표 확인', '요즘 성장하는 회사는?', '반도체 업황 정리', 'DartLab 뭐 할 수 있니'];

function createAssistantMessage() {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    text: '',
    activities: [],
    tools: [],
    refs: [],
    status: 'running',
    failure: null,
  };
}

export default function DartLabApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const activeRunRef = useRef(null);

  const lastAssistant = useMemo(() => [...messages].reverse().find((msg) => msg.role === 'assistant'), [messages]);

  const submit = useCallback(
    async (overrideText) => {
      const text = (overrideText ?? input).trim();
      if (!text || running) return;

      const userMessage = { id: crypto.randomUUID(), role: 'user', text };
      const assistantMessage = createAssistantMessage();
      setMessages((current) => [...current, userMessage, assistantMessage]);
      setInput('');
      setRunning(true);

      const controller = new AbortController();
      activeRunRef.current = controller;

      try {
        await streamAgentRun({
          body: {
            threadId: 'dartlab-local-thread',
            agentId: 'dartlab-research',
            model: 'dartlab-research-graph',
            messages: [{ role: 'user', content: text }],
            stream: true,
          },
          signal: controller.signal,
          onEvent: (event, payload) => {
            setMessages((current) =>
              current.map((message) => {
                if (message.id !== assistantMessage.id) return message;
                return reduceAssistantEvent(message, event, payload);
              }),
            );
          },
        });
      } catch (error) {
        if (error.name !== 'AbortError') {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessage.id
                ? { ...message, status: 'failed', failure: 'agent gateway 연결 실패' }
                : message,
            ),
          );
        }
      } finally {
        setRunning(false);
        activeRunRef.current = null;
      }
    },
    [input, running],
  );

  return (
    <div className="dartlab-app">
      <aside className={`dartlab-sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="brand-mark">
          <Bot size={18} />
        </div>
        <button className="icon-button" title="새 대화" type="button" onClick={() => setMessages([])}>
          <Plus size={18} />
        </button>
        <button className="icon-button active" title="채팅" type="button">
          <Sparkles size={18} />
        </button>
        <button className="icon-button" title="근거" type="button">
          <FileText size={18} />
        </button>
      </aside>

      <main className="dartlab-main">
        <header className="topbar">
          <button className="ghost-button" title="사이드바" type="button" onClick={() => setSidebarOpen((value) => !value)}>
            <Menu size={18} />
          </button>
          <div className="topbar-spacer" />
          <button className="ghost-button" title="근거 패널" type="button">
            <PanelRight size={18} />
          </button>
          <button className="ghost-button" title="설정" type="button">
            <Settings2 size={18} />
          </button>
          <div className="model-chip">
            <span className="model-dot" />
            GPT / gpt-5.4
          </div>
        </header>

        <section className={`conversation ${messages.length === 0 ? 'empty' : ''}`}>
          {messages.length === 0 ? (
            <StartScreen input={input} setInput={setInput} submit={submit} running={running} />
          ) : (
            <div className="message-stack">
              {messages.map((message) =>
                message.role === 'user' ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AssistantMessage key={message.id} message={message} />
                ),
              )}
            </div>
          )}
        </section>

        {messages.length > 0 && (
          <Composer
            input={input}
            setInput={setInput}
            submit={submit}
            running={running}
            onStop={() => activeRunRef.current?.abort()}
          />
        )}

        {lastAssistant?.refs?.length > 0 && <SourceDock refs={lastAssistant.refs} />}
      </main>
    </div>
  );
}

function StartScreen({ input, setInput, submit, running }) {
  return (
    <div className="start-screen">
      <div className="avatar-orbit">
        <Bot size={30} />
      </div>
      <Composer input={input} setInput={setInput} submit={submit} running={running} centered />
      <div className="suggestion-row">
        {INITIAL_SUGGESTIONS.map((item) => (
          <button key={item} type="button" onClick={() => submit(item)}>
            {item}
          </button>
        ))}
      </div>
    </div>
  );
}

function Composer({ input, setInput, submit, running, onStop, centered = false }) {
  return (
    <form
      className={`composer ${centered ? 'centered' : ''}`}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <input
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="메시지를 입력하세요... (/ 로 명령어)"
        disabled={running}
      />
      <button className="send-button" type={running ? 'button' : 'submit'} onClick={running ? onStop : undefined} title={running ? '중지' : '전송'}>
        {running ? <Circle size={17} /> : <Send size={17} />}
      </button>
    </form>
  );
}

function UserMessage({ message }) {
  return (
    <div className="user-row">
      <div className="speaker-label">YOU</div>
      <div className="user-bubble">{message.text}</div>
    </div>
  );
}

function AssistantMessage({ message }) {
  const visibleActivities = message.status === 'running' ? message.activities.slice(-6) : message.activities;
  return (
    <div className="assistant-row">
      <div className="assistant-kicker">
        <StatusIcon status={message.status === 'running' ? 'running' : message.status === 'failed' ? 'failed' : 'done'} />
        <span>{message.status === 'running' ? '작업 중' : message.status === 'failed' ? '실패' : `명령어 ${message.activities.length}개 실행`}</span>
        {message.refs.length > 0 && <span className="mini-pill">근거 {message.refs.length}개</span>}
      </div>

      {message.status === 'running' && visibleActivities.length > 0 && (
        <div className="activity-list">
          {visibleActivities.map((activity) => (
            <div className="activity-item" key={activity.id}>
              <StatusIcon status={activity.status} />
              <span>{activity.summary}</span>
            </div>
          ))}
        </div>
      )}

      {message.status !== 'running' && visibleActivities.length > 0 && (
        <details className="activity-details">
          <summary>작업 내역 보기</summary>
          <div className="activity-list">
            {visibleActivities.map((activity) => (
              <div className="activity-item" key={activity.id}>
                <StatusIcon status={activity.status} />
                <span>{activity.summary}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {message.tools.map((tool) => (
        <ToolCard key={tool.id} tool={tool} />
      ))}

      {message.failure && (
        <div className="failure-notice">
          <AlertTriangle size={17} />
          <div>
            <strong>{message.failure}</strong>
            <span>근거 패널에서 원인을 확인할 수 있습니다.</span>
          </div>
        </div>
      )}

      {message.text && <div className="assistant-text">{message.text}</div>}

      {message.refs.length > 0 && (
        <button className="source-strip" type="button">
          <FileText size={16} />
          근거 refs {message.refs.length}개
          <ChevronDown size={14} />
        </button>
      )}
    </div>
  );
}

function ToolCard({ tool }) {
  return (
    <div className="tool-card">
      <div className="tool-title">
        <SquareTerminal size={16} />
        <strong>{tool.toolName} 실행함</strong>
        <StatusIcon status={tool.status} />
      </div>
      {tool.summary && <div className="tool-summary">{tool.summary}</div>}
    </div>
  );
}

function SourceDock({ refs }) {
  return (
    <aside className="source-dock">
      <div className="dock-title">
        <Search size={15} />
        Evidence
      </div>
      {refs.slice(0, 8).map((ref) => (
        <div className="dock-ref" key={ref}>
          {ref}
        </div>
      ))}
    </aside>
  );
}

function Spinner({ active }) {
  return <span className={`spinner ${active ? 'active' : ''}`} />;
}

function StatusIcon({ status }) {
  if (status === 'failed' || status === 'error') return <AlertTriangle className="status-error" size={14} />;
  if (status === 'running') return <Spinner active />;
  return <CheckCircle2 className="status-done" size={14} />;
}

function reduceAssistantEvent(message, event, payload) {
  if (event === 'ACTIVITY_DELTA') {
    return {
      ...message,
      activities: [
        ...message.activities,
        {
          id: crypto.randomUUID(),
          summary: payload.summary || '작업을 진행합니다.',
          status: payload.status || 'done',
          refs: payload.refs || [],
        },
      ],
    };
  }
  if (event === 'TEXT_MESSAGE_CONTENT') {
    return { ...message, text: message.text + (payload.delta || '') };
  }
  if (event === 'TOOL_CALL_START') {
    return {
      ...message,
      tools: upsertTool(message.tools, {
        id: payload.toolCallId,
        toolName: payload.toolName,
        status: 'running',
        summary: '',
      }),
    };
  }
  if (event === 'TOOL_CALL_RESULT') {
    return {
      ...message,
      tools: upsertTool(message.tools, {
        id: payload.toolCallId,
        toolName: payload.toolName,
        status: payload.status || 'done',
        summary: payload.summary || '',
      }),
    };
  }
  if (event === 'TOOL_CALL_END') {
    return {
      ...message,
      tools: message.tools.map((tool) =>
        tool.id === payload.toolCallId ? { ...tool, status: payload.status || 'done' } : tool,
      ),
    };
  }
  if (event === 'RUN_ERROR') {
    return { ...message, status: 'failed', failure: payload.message || '응답 생성 실패' };
  }
  if (event === 'RUN_FINISHED') {
    return {
      ...message,
      status: payload.status === 'ok' ? 'done' : 'failed',
      refs: payload.refs || [],
      failure: payload.status === 'ok' ? message.failure : message.failure || '응답 생성 실패',
    };
  }
  return message;
}

function upsertTool(tools, nextTool) {
  const exists = tools.some((tool) => tool.id === nextTool.id);
  if (!exists) return [...tools, nextTool];
  return tools.map((tool) => (tool.id === nextTool.id ? { ...tool, ...nextTool } : tool));
}

async function streamAgentRun({ body, signal, onEvent }) {
  const response = await fetch('/api/agent/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`agent run failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || '';
    for (const frame of frames) {
      const parsed = parseSseFrame(frame);
      if (parsed) onEvent(parsed.event, parsed.payload);
    }
  }
}

function parseSseFrame(frame) {
  const eventLine = frame.split(/\r?\n/).find((line) => line.startsWith('event:'));
  const dataLines = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart());
  if (!eventLine || dataLines.length === 0) return null;
  return {
    event: eventLine.slice(6).trim(),
    payload: JSON.parse(dataLines.join('\n')),
  };
}
