<script lang="ts">
  /**
   * Dev shell — fixture jsonl 을 fetch 해서 sseHandler 가 받는 형식으로
   * 시간차 dispatch. MessageBubble 컴포넌트를 직접 mount 해서
   * 실제 렌더링 경로를 검증한다.
   */
  import MessageBubble from "../src/lib/components/MessageBubble.svelte";
  import { createSseHandler, createMessageId, type Message } from "../src/lib/api/sseHandler";

  let message = $state<Message>(makeFresh());
  let playing = $state(false);
  let activeFixture = $state<string>("");

  function makeFresh(): Message {
    return {
      id: createMessageId(),
      role: "assistant",
      text: "",
      blocks: [],
      loading: true,
      error: false,
      startedAt: Date.now(),
    };
  }

  function reset() {
    message = makeFresh();
    activeFixture = "";
  }

  async function play(fixture: string) {
    if (playing) return;
    playing = true;
    activeFixture = fixture;
    message = makeFresh();

    const res = await fetch(`./fixtures/${fixture}.jsonl`);
    const text = await res.text();
    const lines = text.split("\n").filter((l) => l.trim());

    const handler = createSseHandler(
      () => message,
      (patch) => {
        message = { ...message, ...patch };
      },
      () => {
        playing = false;
      },
    );

    // Test marker — Playwright 가 재생 완료를 감지하도록
    document.body.dataset.playState = "playing";
    document.body.dataset.fixture = fixture;

    for (const line of lines) {
      let parsed: { event: string; data: unknown; delay?: number };
      try {
        parsed = JSON.parse(line);
      } catch {
        continue;
      }
      handler.handleEvent(parsed.event, parsed.data);
      const delay = parsed.delay ?? 30;
      if (delay > 0) await sleep(delay);
    }
    handler.handleEvent("done", {});
    handler.handleStreamEnd();

    document.body.dataset.playState = "done";
  }

  function sleep(ms: number) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // URL ?fixture=table&autoplay=1 지원 — Playwright 자동 재생용
  // ?pauseAt=N — N번째 이벤트 후 재생 일시정지 (mid-stream 캡처)
  $effect(() => {
    const params = new URLSearchParams(window.location.search);
    const fx = params.get("fixture");
    const pauseAt = parseInt(params.get("pauseAt") ?? "", 10);
    if (fx && params.get("autoplay") === "1" && !playing && !activeFixture) {
      playWithPause(fx, isFinite(pauseAt) ? pauseAt : -1);
    }
  });

  async function playWithPause(fixture: string, pauseAt: number) {
    if (pauseAt < 0) return play(fixture);
    if (playing) return;
    playing = true;
    activeFixture = fixture;
    message = makeFresh();

    const res = await fetch(`./fixtures/${fixture}.jsonl`);
    const text = await res.text();
    const lines = text.split("\n").filter((l) => l.trim());

    const handler = createSseHandler(
      () => message,
      (patch) => {
        message = { ...message, ...patch };
      },
      () => {},
    );

    document.body.dataset.playState = "playing";
    document.body.dataset.fixture = fixture;

    const upto = Math.min(pauseAt, lines.length);
    for (let i = 0; i < upto; i++) {
      const line = lines[i];
      let parsed: { event: string; data: unknown; delay?: number };
      try {
        parsed = JSON.parse(line);
      } catch {
        continue;
      }
      handler.handleEvent(parsed.event, parsed.data);
      const delay = parsed.delay ?? 30;
      if (delay > 0) await sleep(delay);
    }
    // pause 모드: done 이벤트 보내지 않음 — 메시지가 loading=true 상태로 멈춤
    document.body.dataset.playState = "paused";
    playing = false;
  }
</script>

<div class="dev-root">
  <header class="dev-header">
    <h1>dartlab webview dev harness</h1>
    <div class="controls">
      <button onclick={() => play("table")} disabled={playing}>📊 table</button>
      <button onclick={() => play("chart")} disabled={playing}>📈 chart</button>
      <button onclick={() => play("mixed")} disabled={playing}>🧩 mixed</button>
      <button onclick={reset} disabled={playing} class="reset">↺ reset</button>
      <span class="state">
        {#if playing}재생 중... ({activeFixture})
        {:else if activeFixture}완료 ({activeFixture})
        {:else}대기{/if}
      </span>
    </div>
  </header>
  <main class="dev-main">
    <div class="message-frame">
      <MessageBubble {message} isLast={true} />
    </div>
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    background: #1e1e1e;
    color: #ccc;
    font: 13px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  .dev-root {
    max-width: 920px;
    margin: 0 auto;
    padding: 16px;
  }
  .dev-header {
    border-bottom: 1px solid #333;
    padding-bottom: 12px;
    margin-bottom: 16px;
  }
  .dev-header h1 {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 500;
    color: #888;
    letter-spacing: 0.5px;
  }
  .controls {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }
  .controls button {
    background: #2d2d2d;
    color: #ddd;
    border: 1px solid #404040;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
  }
  .controls button:hover:not(:disabled) {
    background: #3a3a3a;
  }
  .controls button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .controls .reset {
    background: transparent;
  }
  .state {
    margin-left: auto;
    font-size: 11px;
    color: #888;
  }
  .message-frame {
    background: #252526;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 16px;
    min-height: 200px;
  }
</style>
