<script lang="ts">
	import { onMount } from 'svelte';

	const HF = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
	const WHEEL_URL = `${HF}/pyodide/dartlab-0.9.8-py3-none-any.whl`;
	const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js';

	const BUILTINS = [
		'polars', 'pyarrow', 'micropip', 'beautifulsoup4', 'lxml',
		'httpx', 'pydantic', 'rich', 'sqlite3', 'numpy'
	];
	const PURE_DEPS = ['diff-match-patch', 'openpyxl'];
	const CATS = [
		{ dir: 'dart/docs', name: 'docs' },
		{ dir: 'dart/finance', name: 'finance' },
		{ dir: 'dart/report', name: 'report' }
	];

	let logs = $state<string[]>([]);
	let stockCode = $state('005930');
	let loading = $state(false);
	let ready = $state(false);
	let pyodide: any = null;

	// AI
	let aiProvider = $state('gemini');
	let apiKey = $state('');
	let aiLoading = $state(false);

	function log(msg: string) {
		logs = [...logs, msg];
	}

	async function init() {
		if (loading || ready) return;
		loading = true;
		logs = [];

		try {
			log('[1/5] Pyodide 로드...');
			const script = document.createElement('script');
			script.src = PYODIDE_CDN;
			document.head.appendChild(script);
			await new Promise<void>((resolve) => { script.onload = () => resolve(); });
			pyodide = await (globalThis as any).loadPyodide();
			log(`  Pyodide ${pyodide.version}`);

			log('[2/5] 패키지 로드...');
			await pyodide.loadPackage(BUILTINS);

			log('[3/5] dartlab 설치...');
			const wheelResp = await fetch(WHEEL_URL);
			const wheelBuf = new Uint8Array(await wheelResp.arrayBuffer());
			pyodide.FS.writeFile('/tmp/dartlab.whl', wheelBuf);
			log(`  ${(wheelBuf.length / 1024).toFixed(0)} KB`);

			await pyodide.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(PURE_DEPS)})
import zipfile, site
whl = zipfile.ZipFile("/tmp/dartlab.whl")
sp = site.getsitepackages()[0] if site.getsitepackages() else "/lib/python3.12/site-packages"
whl.extractall(sp)
whl.close()
			`);

			log('[4/5] 데이터 다운로드...');
			for (const cat of CATS) {
				const r = await fetch(`${HF}/${cat.dir}/${stockCode}.parquet`);
				if (!r.ok) { log(`  ⚠ ${cat.name} 실패`); continue; }
				const buf = new Uint8Array(await r.arrayBuffer());
				pyodide.FS.mkdirTree(`/data/${cat.dir}`);
				pyodide.FS.writeFile(`/data/${cat.dir}/${stockCode}.parquet`, buf);
				log(`  ${cat.name}: ${(buf.length / 1024).toFixed(0)} KB`);
			}

			log('[5/5] dartlab 초기화...');
			pyodide.setStdout({ batched: (msg: string) => log('  ' + msg) });
			await pyodide.runPythonAsync(`
import dartlab
c = dartlab.Company("${stockCode}")
			`);
			log(`  Company(${stockCode}) 준비 완료`);
			ready = true;
		} catch (e: any) {
			log('❌ ' + (e.message || e));
		} finally {
			loading = false;
		}
	}

	async function run(label: string, code: string) {
		if (!ready) return;
		log(`\n▶ ${label}`);
		try {
			await pyodide.runPythonAsync(code);
		} catch (e: any) {
			log('❌ ' + (e.message || '').slice(0, 300));
		}
	}

	async function runAsk() {
		if (!ready || !apiKey.trim()) return;
		aiLoading = true;
		log(`\n▶ AI ask (${aiProvider})...`);
		try {
			const envMap: Record<string, string[]> = {
				gemini: ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
				openai: ['OPENAI_API_KEY']
			};
			for (const k of envMap[aiProvider] || []) {
				await pyodide.runPythonAsync(`import os; os.environ["${k}"] = "${apiKey.trim()}"`);
			}
			await pyodide.runPythonAsync(`
import traceback, io
try:
    answer = dartlab.ask("${stockCode} 수익성 분석해줘", provider="${aiProvider}", stream=False)
    if answer:
        print(answer[:2000])
    else:
        print("응답 없음")
except Exception:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
			`);
		} catch (e: any) {
			log('❌ ' + (e.message || '').slice(0, 300));
		} finally {
			aiLoading = false;
		}
	}

	let logEl: HTMLPreElement;
	$effect(() => {
		if (logEl) logEl.scrollTop = logEl.scrollHeight;
	});
</script>

<svelte:head>
	<title>Playground — dartlab 전자공시 재무분석</title>
	<meta name="description" content="브라우저에서 바로 실행하는 한국 전자공시 재무분석. 설치 없이 dartlab을 체험하세요." />
</svelte:head>

<div class="dl-playground">
	<h1>dartlab playground</h1>
	<p class="desc">브라우저에서 바로 실행. 설치 없음.</p>

	<div class="controls">
		<input
			type="text"
			bind:value={stockCode}
			placeholder="종목코드"
			class="input-stock"
			disabled={loading || ready}
		/>
		<button onclick={init} disabled={loading || ready}>
			{#if loading}로딩 중...{:else if ready}✓ 준비 완료{:else}시작{/if}
		</button>
	</div>

	{#if ready}
		<div class="actions">
			<button onclick={() => run('손익계산서', 'print(c.show("IS"))')}>show IS</button>
			<button onclick={() => run('재무상태표', 'print(c.show("BS"))')}>show BS</button>
			<button onclick={() => run('수익성 분석', `
r = c.analysis("financial", "수익성")
if r:
    for k,v in r.items():
        print(f"  {k}: {type(v).__name__}")
			`)}>analysis 수익성</button>
			<button onclick={() => run('review 수익성', `
import traceback, io
try:
    print(c.review("수익성").toMarkdown())
except Exception:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
			`)}>review 수익성</button>
		</div>

		<div class="ai-bar">
			<select bind:value={aiProvider}>
				<option value="gemini">Gemini</option>
				<option value="openai">OpenAI</option>
			</select>
			<input type="password" bind:value={apiKey} placeholder="API 키" class="input-key" />
			<button onclick={runAsk} disabled={aiLoading || !apiKey.trim()}>
				{#if aiLoading}분석 중...{:else}AI ask{/if}
			</button>
		</div>
	{/if}

	<pre class="log" bind:this={logEl}>{logs.join('\n')}</pre>
</div>

<style>
	.dl-playground {
		max-width: 960px;
		margin: 0 auto;
		padding: 2rem 1rem;
		font-family: ui-monospace, Menlo, Consolas, monospace;
	}
	h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
	.desc { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }
	.controls, .actions, .ai-bar {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
		flex-wrap: wrap;
	}
	.input-stock { width: 120px; padding: 6px 10px; font-family: inherit; font-size: 0.9rem; }
	.input-key { width: 280px; padding: 6px 10px; font-family: inherit; font-size: 0.85rem; }
	button {
		padding: 6px 14px;
		font-size: 0.85rem;
		cursor: pointer;
		border: 1px solid #ccc;
		border-radius: 4px;
		background: #fff;
	}
	button:hover:not(:disabled) { background: #f5f5f5; }
	button:disabled { opacity: 0.5; cursor: default; }
	select { padding: 6px 8px; font-family: inherit; }
	.log {
		background: #111;
		color: #0f0;
		padding: 12px;
		border-radius: 6px;
		min-height: 300px;
		max-height: 70vh;
		overflow-y: auto;
		font-size: 0.75rem;
		white-space: pre-wrap;
		line-height: 1.4;
	}
</style>
