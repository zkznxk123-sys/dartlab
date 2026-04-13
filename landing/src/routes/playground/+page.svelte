<script lang="ts">
	import { base } from '$app/paths';
	const HF = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
	const WHEEL_URL = `${HF}/pyodide/dartlab-0.9.9-py3-none-any.whl`;
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

	type Step = { label: string; status: 'pending' | 'active' | 'done' | 'error' };

	let steps = $state<Step[]>([
		{ label: 'Pyodide 엔진', status: 'pending' },
		{ label: '패키지 로드', status: 'pending' },
		{ label: 'dartlab 설치', status: 'pending' },
		{ label: '데이터 다운로드', status: 'pending' },
		{ label: '초기화', status: 'pending' },
	]);
	let logs = $state<string[]>([]);
	let stockCode = $state('005930');
	let loading = $state(false);
	let ready = $state(false);
	let pyodide: any = null;

	let aiProvider = $state('gemini');
	let apiKey = $state('');
	let aiLoading = $state(false);

	function setStep(idx: number, status: Step['status']) {
		steps = steps.map((s, i) => i === idx ? { ...s, status } : s);
	}
	function log(msg: string) {
		logs = [...logs, msg];
	}

	async function init() {
		if (loading || ready) return;
		loading = true;
		logs = [];

		try {
			// 1. Pyodide
			setStep(0, 'active');
			const script = document.createElement('script');
			script.src = PYODIDE_CDN;
			document.head.appendChild(script);
			await new Promise<void>((r) => { script.onload = () => r(); });
			pyodide = await (globalThis as any).loadPyodide();
			log(`Pyodide ${pyodide.version}`);
			setStep(0, 'done');

			// 2. 패키지
			setStep(1, 'active');
			await pyodide.loadPackage(BUILTINS);
			setStep(1, 'done');

			// 3. wheel
			setStep(2, 'active');
			const wheelResp = await fetch(WHEEL_URL);
			if (!wheelResp.ok) throw new Error(`wheel 다운로드 실패 (${wheelResp.status})`);
			const wheelBuf = new Uint8Array(await wheelResp.arrayBuffer());
			pyodide.FS.writeFile('/tmp/dartlab.whl', wheelBuf);
			log(`dartlab ${(wheelBuf.length / 1024 / 1024).toFixed(1)} MB`);
			await pyodide.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(PURE_DEPS)})
import zipfile, site
whl = zipfile.ZipFile("/tmp/dartlab.whl")
sp = site.getsitepackages()[0] if site.getsitepackages() else "/lib/python3.12/site-packages"
whl.extractall(sp)
whl.close()
			`);
			setStep(2, 'done');

			// 4. 데이터
			setStep(3, 'active');
			for (const cat of CATS) {
				const r = await fetch(`${HF}/${cat.dir}/${stockCode}.parquet`);
				if (!r.ok) { log(`⚠ ${cat.name} 실패`); continue; }
				const buf = new Uint8Array(await r.arrayBuffer());
				pyodide.FS.mkdirTree(`/data/${cat.dir}`);
				pyodide.FS.writeFile(`/data/${cat.dir}/${stockCode}.parquet`, buf);
				log(`${cat.name} ${(buf.length / 1024).toFixed(0)} KB`);
			}
			setStep(3, 'done');

			// 5. 초기화
			setStep(4, 'active');
			pyodide.setStdout({ batched: (msg: string) => log(msg) });
			await pyodide.runPythonAsync(`
import dartlab
c = dartlab.Company("${stockCode}")
			`);
			log(`Company(${stockCode}) 준비 완료`);
			setStep(4, 'done');
			ready = true;
		} catch (e: any) {
			log('❌ ' + (e.message || e));
			const activeIdx = steps.findIndex(s => s.status === 'active');
			if (activeIdx >= 0) setStep(activeIdx, 'error');
		} finally {
			loading = false;
		}
	}

	async function run(code: string) {
		if (!ready) return;
		try {
			await pyodide.runPythonAsync(code);
		} catch (e: any) {
			log('❌ ' + (e.message || '').slice(0, 500));
		}
	}

	async function runAsk() {
		if (!ready || !apiKey.trim()) return;
		aiLoading = true;
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
        print(answer)
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

	const commands = [
		{ label: 'show IS', desc: '손익계산서', code: 'print(c.show("IS"))' },
		{ label: 'show BS', desc: '재무상태표', code: 'print(c.show("BS"))' },
		{ label: 'show CF', desc: '현금흐름표', code: 'print(c.show("CF"))' },
		{ label: 'analysis', desc: '수익성 분석', code: `
r = c.analysis("financial", "수익성")
if r:
    for k,v in r.items(): print(f"  {k}: {type(v).__name__}")
		` },
		{ label: 'review', desc: '6막 보고서', code: `
import traceback, io
try:
    print(c.review("수익성").toMarkdown())
except Exception:
    buf = io.StringIO(); traceback.print_exc(file=buf); print(buf.getvalue())
		` },
	];

	let logEl: HTMLPreElement;
	$effect(() => {
		if (logEl && logs.length) logEl.scrollTop = logEl.scrollHeight;
	});
</script>

<svelte:head>
	<title>Playground — dartlab 전자공시 재무분석</title>
	<meta name="description" content="브라우저에서 바로 실행하는 한국 전자공시 재무분석. 설치 없이 dartlab을 체험하세요." />
</svelte:head>

<div class="min-h-screen bg-dl-bg-dark text-dl-text">
	<div class="mx-auto max-w-4xl px-6 pt-20 pb-16">
		<!-- Header -->
		<div class="mb-10">
			<a href="{base}/" class="text-dl-text-muted text-sm hover:text-dl-text transition-colors">← dartlab</a>
			<h1 class="text-3xl font-bold mt-3 mb-2">Playground</h1>
			<p class="text-dl-text-muted">브라우저에서 바로 실행. 설치 없음.</p>
		</div>

		<!-- Init -->
		{#if !ready}
			<div class="rounded-lg border border-dl-border bg-dl-bg-card p-6 mb-6">
				<div class="flex items-center gap-3 mb-5">
					<input
						type="text"
						bind:value={stockCode}
						placeholder="종목코드"
						disabled={loading}
						class="w-28 px-3 py-2 rounded bg-dl-bg-dark border border-dl-border text-dl-text font-mono text-sm focus:border-dl-primary outline-none"
					/>
					<button
						onclick={init}
						disabled={loading}
						class="px-5 py-2 rounded font-medium text-sm transition-colors
							{loading ? 'bg-dl-bg-dark text-dl-text-muted cursor-wait' : 'bg-dl-primary text-white hover:bg-dl-primary-dark cursor-pointer'}"
					>
						{#if loading}초기화 중...{:else}시작{/if}
					</button>
				</div>

				<!-- Steps -->
				<div class="flex flex-col gap-2">
					{#each steps as step, i}
						<div class="flex items-center gap-3 text-sm">
							<span class="w-5 h-5 flex items-center justify-center rounded-full text-xs font-bold
								{step.status === 'done' ? 'bg-dl-success/20 text-dl-success' :
								 step.status === 'active' ? 'bg-dl-primary/20 text-dl-primary' :
								 step.status === 'error' ? 'bg-red-500/20 text-red-400' :
								 'bg-dl-border text-dl-text-dim'}">
								{#if step.status === 'done'}✓
								{:else if step.status === 'active'}
									<span class="animate-spin">⟳</span>
								{:else if step.status === 'error'}✗
								{:else}{i + 1}{/if}
							</span>
							<span class="{step.status === 'done' ? 'text-dl-text' : step.status === 'active' ? 'text-dl-primary' : 'text-dl-text-dim'}">
								{step.label}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Commands -->
		{#if ready}
			<div class="rounded-lg border border-dl-border bg-dl-bg-card p-5 mb-4">
				<div class="flex flex-wrap gap-2 mb-4">
					{#each commands as cmd}
						<button
							onclick={() => run(cmd.code)}
							class="px-3 py-1.5 rounded text-sm border border-dl-border bg-dl-bg-dark
								hover:border-dl-primary hover:text-dl-primary transition-colors cursor-pointer"
							title={cmd.desc}
						>
							{cmd.label}
						</button>
					{/each}
				</div>

				<!-- AI -->
				<div class="flex items-center gap-2 pt-3 border-t border-dl-border">
					<select
						bind:value={aiProvider}
						class="px-2 py-1.5 rounded text-sm bg-dl-bg-dark border border-dl-border text-dl-text"
					>
						<option value="gemini">Gemini</option>
						<option value="openai">OpenAI</option>
					</select>
					<input
						type="password"
						bind:value={apiKey}
						placeholder="API 키"
						class="flex-1 max-w-xs px-3 py-1.5 rounded text-sm bg-dl-bg-dark border border-dl-border text-dl-text font-mono focus:border-dl-primary outline-none"
					/>
					<button
						onclick={runAsk}
						disabled={aiLoading || !apiKey.trim()}
						class="px-4 py-1.5 rounded text-sm font-medium transition-colors cursor-pointer
							{aiLoading ? 'bg-dl-bg-dark text-dl-text-muted cursor-wait' :
							 !apiKey.trim() ? 'bg-dl-bg-dark text-dl-text-dim cursor-not-allowed' :
							 'bg-dl-accent text-white hover:bg-dl-accent-light'}"
					>
						{#if aiLoading}분석 중...{:else}AI ask{/if}
					</button>
				</div>
			</div>
		{/if}

		<!-- Output -->
		<pre
			class="rounded-lg bg-dl-bg-card border border-dl-border p-4 min-h-48 max-h-[60vh] overflow-y-auto text-xs font-mono text-dl-text-muted leading-relaxed whitespace-pre-wrap"
			bind:this={logEl}
		>{logs.join('\n')}</pre>
	</div>
</div>
