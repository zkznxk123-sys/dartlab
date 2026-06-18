<script lang="ts">
	// 전략 백테스트 도크 — 차트 워크스페이스 좌측 영구 패널(드랍다운 폐기 SSOT). 차트 클릭/팬/줌에 안 닫힘.
	//   헤더(접기·닫기) · 컨텍스트(종목·일봉) · ① 전략(조건 빌더) · ② 손절/익절 · ③ 검증(비용·OOS·게이트) · 결과 푸터(HonestyFooter).
	// BtConfig 의 조건 빌더 로직을 그대로 흡수(ctl.bt* 변이 → PriceChart $effect 재계산, tweak→see 무배선). 그래프 금지(3열 규칙) — equity 는 차트.
	// 접기=28px 스파인(결과 유지), 닫기=clearBtAll+도크 off(맨 차트 복귀). 폭 리사이즈(260~420).
	import type { Lang } from '../lib/types';
	import type { ChartCtl } from './chartState.svelte';
	import type { PortfolioBtResult } from '../lib/backtest';
	import { BT_PRESETS, BT_COSTS, RULE_PRESETS, SERIES_CATALOG, OP_LABEL } from '../lib/backtest';
	import type { Op, SeriesKey, StrategyRule } from '../lib/backtest';
	import HonestyFooter from './HonestyFooter.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		pf?: PortfolioBtResult | null; // 결과(있으면 하단 푸터) — fill(좌패널) 모드에선 미전달(결과는 중앙 하단 보고서)
		code?: string;
		name?: string;
		fill?: boolean; // true = 좌측 패널 전체 차지(폭 100%·리사이즈·접기 없음). false = 차트 좌측 도크(레거시)
		onOpenReport?: () => void;
		onClose: () => void; // = clearBtAll + 백테스트 모드 종료
	}
	let { ctl, lang, pf = null, code, name, fill = false, onOpenReport, onClose }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const OPS: Op[] = ['>', '<', '>=', '<=', 'crossUp', 'crossDown'];
	const seriesDef = (key: SeriesKey) => SERIES_CATALOG.find((s) => s.key === key);

	let collapsed = $state(false);
	// 폭 리사이즈 — 드래그 핸들(우측 가장자리). 세션 한정 $state.
	let dockW = $state(320);
	function startResize(e: PointerEvent) {
		e.preventDefault();
		const startX = e.clientX;
		const startW = dockW;
		const move = (ev: PointerEvent) => { dockW = Math.max(260, Math.min(420, startW + (ev.clientX - startX))); };
		const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
		window.addEventListener('pointermove', move);
		window.addEventListener('pointerup', up);
	}

	const COST_FIELDS = [
		{ k: 'commissionBp' as const, kr: '수수료', en: 'fee', min: 0, max: 10, step: 0.5 },
		{ k: 'sellTaxBp' as const, kr: '거래세', en: 'tax', min: 0, max: 30, step: 1 },
		{ k: 'slippageBp' as const, kr: '슬리피지', en: 'slip', min: 0, max: 50, step: 5 }
	];
	function stepCost(k: (typeof COST_FIELDS)[number], dir: 1 | -1) {
		const next = Math.max(k.min, Math.min(k.max, +(ctl.btCostsBp[k.k] + dir * k.step).toFixed(1)));
		ctl.btCostsBp = { ...ctl.btCostsBp, [k.k]: next };
	}
	const costsDefault = $derived(ctl.btCostsBp.commissionBp === BT_COSTS.commissionBp && ctl.btCostsBp.sellTaxBp === BT_COSTS.sellTaxBp && ctl.btCostsBp.slippageBp === BT_COSTS.slippageBp);
	function stepStop(k: 'lossPct' | 'gainPct', dir: 1 | -1) {
		const cur = ctl.btStop[k] ?? 0;
		const next = Math.max(0, Math.min(50, cur + dir * 2));
		ctl.btStop = { ...ctl.btStop, [k]: next === 0 ? undefined : next };
	}

	// ── 룰 불변 편집 — 슬롯의 rule 을 clone·변형 후 setSlotRule ──
	function editRule(i: number, fn: (r: StrategyRule) => void) {
		const slot = ctl.btStrategies[i];
		if (!slot?.rule) return;
		const r = structuredClone(slot.rule);
		fn(r);
		ctl.setSlotRule(i, r);
	}
	const sideArr = (r: StrategyRule, side: 'entry' | 'exit') => (side === 'entry' ? r.entry : r.exit);
	function setLeft(i: number, side: 'entry' | 'exit', ci: number, key: SeriesKey) {
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.left = key; c.leftParams = Object.fromEntries((seriesDef(key)?.params ?? []).map((p) => [p.name, p.def])); });
	}
	function stepLeftParam(i: number, side: 'entry' | 'exit', ci: number, name: string, dir: 1 | -1) {
		const pp = seriesDef(sideArr(ctl.btStrategies[i].rule!, side)[ci].left)?.params.find((p) => p.name === name);
		if (!pp) return;
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; const v = c.leftParams[name] ?? pp.def; c.leftParams[name] = Math.max(pp.min, Math.min(pp.max, +(v + dir * pp.step).toFixed(2))); });
	}
	function setOp(i: number, side: 'entry' | 'exit', ci: number, op: Op) { editRule(i, (r) => { sideArr(r, side)[ci].op = op; }); }
	function setRightKind(i: number, side: 'entry' | 'exit', ci: number, kind: 'const' | 'series') {
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.right = kind === 'const' ? { kind: 'const', value: 0 } : { kind: 'series', key: 'ma', params: { period: 60 } }; });
	}
	function setRightConst(i: number, side: 'entry' | 'exit', ci: number, value: number) { editRule(i, (r) => { const c = sideArr(r, side)[ci]; if (c.right.kind === 'const') c.right.value = value; }); }
	function setRightSeries(i: number, side: 'entry' | 'exit', ci: number, key: SeriesKey) { editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.right = { kind: 'series', key, params: Object.fromEntries((seriesDef(key)?.params ?? []).map((p) => [p.name, p.def])) }; }); }
	function stepRightParam(i: number, side: 'entry' | 'exit', ci: number, name: string, dir: 1 | -1) {
		const c0 = sideArr(ctl.btStrategies[i].rule!, side)[ci];
		if (c0.right.kind !== 'series') return;
		const pp = seriesDef(c0.right.key)?.params.find((p) => p.name === name);
		if (!pp) return;
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; if (c.right.kind === 'series') { const v = c.right.params[name] ?? pp.def; c.right.params[name] = Math.max(pp.min, Math.min(pp.max, +(v + dir * pp.step).toFixed(2))); } });
	}
	function addCond(i: number, side: 'entry' | 'exit') { editRule(i, (r) => { sideArr(r, side).push({ left: 'price', leftParams: {}, op: side === 'entry' ? '>' : '<', right: { kind: 'series', key: 'ma', params: { period: 60 } } }); }); }
	function removeCond(i: number, side: 'entry' | 'exit', ci: number) { editRule(i, (r) => { sideArr(r, side).splice(ci, 1); }); }
	function setCombine(i: number, side: 'entry' | 'exit', mode: 'AND' | 'OR') { editRule(i, (r) => { if (side === 'entry') r.entryCombine = mode; else r.exitCombine = mode; }); }

	// 접힘 스파인 헤드라인(결과 있으면 수익률 1개)
	const headRet = $derived(pf ? (pf.combo ? pf.combo.metrics.retPct : pf.slots[ctl.btFocus]?.result.metrics.retPct ?? pf.slots[0]?.result.metrics.retPct ?? null) : null);
	const sgn = (v: number) => (v >= 0 ? '+' : '') + v.toFixed(1);
</script>

{#if collapsed && !fill}
	<!-- 접힘 스파인(28px) — 차트 도크 모드에서만. 좌패널(fill) 모드는 접기 없음. -->
	<button class="sdSpine" onclick={() => (collapsed = false)} title={T('전략 도크 펼치기', 'expand strategy dock')}>
		<span class="sdSpineTtl">{T('전략 백테스트', 'STRATEGY LAB')}</span>
		{#if headRet != null}<span class={'sdSpineRet mono ' + (headRet >= 0 ? 'tUp' : 'tDn')}>{sgn(headRet)}%</span>{/if}
	</button>
{:else}
	<div class="stratDock" class:fill style={fill ? '' : `width:${dockW}px`}>
		<!-- 헤더(sticky) -->
		<div class="sdHeader">
			<span class="sdMark" aria-hidden="true"></span>
			<div class="sdTtlWrap">
				<span class="sdTtl">{T('전략 백테스트', 'STRATEGY LAB')}</span>
				<span class="sdSub">{T('규칙 조립 → 차트 위 즉시 검증', 'compose → verify on chart')}</span>
			</div>
			{#if !fill}<button class="sdHbtn" onclick={() => (collapsed = true)} aria-label="collapse" title={T('접기(결과 유지)', 'collapse')}>—</button>{/if}
			<button class="sdHbtn" onclick={onClose} aria-label="close" title={T('백테스트 종료', 'close & exit')}>✕</button>
		</div>

		<div class="sdBody">
			<div class="sdScope">
				{#each [{ v: 'single' as const, kr: '단일종목', en: 'Stock' }, { v: 'market' as const, kr: '시장', en: 'Market' }, { v: 'universe' as const, kr: '유니버스', en: 'Universe' }] as o (o.v)}
					<button class={ctl.btScope === o.v ? 'sdScopeBtn on' : 'sdScopeBtn'} onclick={() => (ctl.btScope = o.v)}>{T(o.kr, o.en)}</button>
				{/each}
			</div>
			<div class="sdScopeNote">{ctl.btScope === 'universe' ? T('전 종목 횡단면 팩터 · 17년 상폐보존 — 제어·결과는 하단 보고서.', 'cross-sectional factor; controls in report below') : ctl.btScope === 'market' ? T('지수 타이밍 — 상단에서 지수를 선택해 시장 백테스트.', 'index timing; pick an index above') : T('이 종목에 매매 규칙을 적용해 검증.', 'apply a rule to this stock')}</div>
			<!-- 컨텍스트 — 종목·봉주기(비파괴 일봉 안내) -->
			<div class="sdCtx">
				<span class="sdCtxSym">{name ?? ''} {code ?? ''}</span>
				<span class="sdCtxMeta">· {T('일봉', 'daily')} · {ctl.period}</span>
			</div>
			{#if ctl.tf !== 'D'}
				<div class="btTfNote">{T('백테스트는 일봉 기준입니다 — 현재 차트는 일봉이 아닙니다.', 'Backtest runs on daily bars — your chart is not on daily.')} <button class="btTfSwitch" onclick={() => (ctl.tf = 'D')}>{T('일봉으로 전환', 'switch to daily')}</button></div>
			{/if}

			<!-- ① 전략 -->
			<div class="btSection">
				<div class="ctMenuLbl">{T('① 전략 (최대 3 · 같은 차트 비교)', '① Strategies (up to 3)')}</div>
				{#if ctl.btStrategies.length === 0}
					<div class="btEmpty">
						<div class="btEmptyDesc">{T('당신의 매매 규칙(진입·청산)을 정의하면 — 미래참조 차단·실제 비용·표본 밖(OOS)으로 정직하게 검증해 차트 위에 그립니다. 아래에서 규칙을 조립하거나 프리셋을 출발점으로 고르세요.', 'Define your entry/exit rule — it is tested honestly (no look-ahead · real costs · out-of-sample) and drawn on the chart. Compose a rule or start from a preset below.')}</div>
				</div>
				{/if}
				{#each ctl.btStrategies as s, i (s.id)}
					<div class="btSlot" class:on={i === ctl.btFocus}>
						<div class="btSlotHd">
							<button class="btSwBtn" onclick={() => ctl.setBtFocus(i)} title={T('포커스', 'focus')} aria-label="focus"><i class="btSw" style={`background:${s.color}`}></i></button>
							<span class="btSlotLbl">{s.label}{#if s.rule}<em class="btRuleTag">{T('규칙', 'rule')}</em>{/if}</span>
							<button class="btDel" onclick={() => ctl.removeStrategy(i)} title={T('삭제', 'remove')} aria-label="remove">✕</button>
						</div>

						{#if i === ctl.btFocus}
							{#if s.rule}
								{@const rule = s.rule}
								{#each ['entry', 'exit'] as const as side (side)}
									{@const conds = side === 'entry' ? rule.entry : rule.exit}
									<div class="condBlk">
										<div class="condHd">
											<span>{side === 'entry' ? T('진입 조건', 'ENTRY') : T('청산 조건', 'EXIT')}</span>
											{#if conds.length > 1}
												<div class="combineTg">
													{#each ['AND', 'OR'] as const as m (m)}
														<button class={(side === 'entry' ? rule.entryCombine : rule.exitCombine) === m ? 'on' : ''} onclick={() => setCombine(i, side, m)}>{m}</button>
													{/each}
												</div>
											{/if}
										</div>
										{#each conds as c, ci (ci)}
											<div class="condRow">
												<select class="condSel" value={c.left} onchange={(e) => setLeft(i, side, ci, e.currentTarget.value as SeriesKey)}>
													<optgroup label={T('가격·기술', 'price/technical')}>
														{#each SERIES_CATALOG as sd (sd.key)}<option value={sd.key}>{T(sd.kr, sd.en)}</option>{/each}
													</optgroup>
													<optgroup label={T('펀더게이트 (재무·panel)', 'fundamental gate')}>
														<option value="fundGate">{T('Piotroski F (재무건강 0~9)', 'Piotroski F (0~9)')}</option>
													</optgroup>
												</select>
												{#each seriesDef(c.left)?.params ?? [] as pp (pp.name)}
													<span class="condP"><button onclick={() => stepLeftParam(i, side, ci, pp.name, -1)}>−</button><b>{c.leftParams[pp.name] ?? pp.def}</b><button onclick={() => stepLeftParam(i, side, ci, pp.name, 1)}>+</button></span>
												{/each}
												<select class="condOp" value={c.op} onchange={(e) => setOp(i, side, ci, e.currentTarget.value as Op)}>
													{#each OPS as op (op)}<option value={op}>{OP_LABEL[op]}</option>{/each}
												</select>
												<select class="condKind" value={c.right.kind} onchange={(e) => setRightKind(i, side, ci, e.currentTarget.value as 'const' | 'series')}>
													<option value="const">{T('값', 'const')}</option>
													<option value="series">{T('지표', 'series')}</option>
												</select>
												{#if c.right.kind === 'const'}
													<input class="condNum mono" type="number" value={c.right.value} onchange={(e) => setRightConst(i, side, ci, +e.currentTarget.value)} />
												{:else}
													<select class="condSel" value={c.right.key} onchange={(e) => setRightSeries(i, side, ci, e.currentTarget.value as SeriesKey)}>
														{#each SERIES_CATALOG as sd (sd.key)}<option value={sd.key}>{T(sd.kr, sd.en)}</option>{/each}
													</select>
													{#each seriesDef(c.right.key)?.params ?? [] as pp (pp.name)}
														<span class="condP"><button onclick={() => stepRightParam(i, side, ci, pp.name, -1)}>−</button><b>{c.right.kind === 'series' ? c.right.params[pp.name] ?? pp.def : pp.def}</b><button onclick={() => stepRightParam(i, side, ci, pp.name, 1)}>+</button></span>
													{/each}
												{/if}
												{#if conds.length > 1}<button class="condDel" onclick={() => removeCond(i, side, ci)} aria-label="remove condition">✕</button>{/if}
											</div>
										{/each}
										<button class="condAdd" onclick={() => addCond(i, side)}>＋ {T('조건', 'condition')}</button>
									</div>
								{/each}
								<div class="btDesc">{T('지표·연산자·임계값을 직접 조합 · 교육·탐색용(추천 아님)', 'compose your own rule · educational (not advice)')}</div>
							{:else}
								{@const pd = BT_PRESETS.find((d) => d.key === s.preset)}
								<div class="btSlotHd">
									<select class="btSelect mono" value={s.preset} onchange={(e) => { const p = BT_PRESETS.find((d) => d.key === e.currentTarget.value); if (p) ctl.setSlotPreset(i, p); }}>
										{#each BT_PRESETS as p (p.key)}<option value={p.key}>{T(p.kr, p.en)}</option>{/each}
									</select>
								</div>
								{#if pd}{#each pd.params as pp (pp.name)}
									<div class="ctRow btParamRow">
										<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
										<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, -1)}>−</button>
										<b class="btParamVal mono">{s.params[pp.name] ?? pp.def}</b>
										<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, 1)}>+</button>
									</div>
								{/each}{/if}
							{/if}
						{/if}
					</div>
				{/each}
				{#if ctl.btStrategies.length < 3}
					<div class="btPresetGrid">
						{#each BT_PRESETS as p (p.key)}<button class="btPresetBtn" onclick={() => ctl.addStrategy(p)} title={T('출발점 · 추천 아님', 'starting point · not advice')}>{T(p.kr, p.en)}</button>{/each}
						{#each RULE_PRESETS as rp (rp.key)}<button class="btPresetBtn rule" onclick={() => ctl.addRulePreset(rp)} title={T('규칙 프리셋(편집가능) · 출발점', 'editable rule preset · starting point')}>{T(rp.kr, rp.en)}</button>{/each}
					</div>
					<div class="btCustomCard">
						<button class="btCustomBtn" onclick={() => ctl.addCustomRule()}>＋ {T('커스텀 규칙 빌더', 'custom rule builder')}</button>
						<span class="btCustomHint">{T('지표·연산자·임계값 직접 조립 · 추천 아님', 'compose indicators/operators/thresholds')}</span>
					</div>
				{/if}
				{#if ctl.btStrategies.length >= 2}
					<div class="btDesc warn">{T('⚠ 여러 전략 같은 데이터 비교 = 사후선택 편향 · 단일종목 조합 = 타이밍 분산이지 자산 분산 아님', 'selection bias · single-stock combo = timing not asset')}</div>
				{/if}
			</div>

			<!-- ② 손절·익절 (공유) -->
			{#if ctl.btStrategies.length}
				<div class="btSection">
					<div class="ctMenuLbl">{T('② 손절·익절 (공유)', '② Stop / Take (shared)')}</div>
					<div class="ctRow btParamRow">
						<span class="btParamLbl">{T('손절', 'stop')}</span>
						<button class="mItem" onclick={() => stepStop('lossPct', -1)}>−</button>
						<b class="btParamVal mono">{ctl.btStop.lossPct != null ? '−' + ctl.btStop.lossPct : '—'}</b>
						<span class="btParamLbl">%</span>
						<button class="mItem" onclick={() => stepStop('lossPct', 1)}>+</button>
					</div>
					<div class="ctRow btParamRow">
						<span class="btParamLbl">{T('익절', 'take')}</span>
						<button class="mItem" onclick={() => stepStop('gainPct', -1)}>−</button>
						<b class="btParamVal mono">{ctl.btStop.gainPct != null ? '+' + ctl.btStop.gainPct : '—'}</b>
						<span class="btParamLbl">%</span>
						<button class="mItem" onclick={() => stepStop('gainPct', 1)}>+</button>
					</div>
					{#if ctl.btStop.lossPct || ctl.btStop.gainPct}<div class="btDesc warn">{T('⚠ 당일 인트라바 가정 — t+1 시가 체결과 시점 충돌(보수: 손절 우선)', 'intraday assumption — conflicts with t+1 fill')}</div>{/if}
				</div>
			{/if}

			<!-- ③ 검증 — 비용 + OOS + 게이트(이것이 결과를 '진짜'로 만든다) -->
			<div class="btSection">
				<div class="ctMenuLbl">{T('③ 검증 — 비용·OOS·게이트 (공유)', '③ Validation — costs · OOS · gate')}</div>
				<!-- (a) 비용 -->
				<div class="ctRow">
					<button class={ctl.btCosts ? 'mItem on' : 'mItem'} onclick={() => (ctl.btCosts = !ctl.btCosts)}>{T('수수료·세금 포함', 'include costs')}</button>
				</div>
				{#if ctl.btCosts}
					{#each COST_FIELDS as cf (cf.k)}
						<div class="ctRow btParamRow">
							<span class="btParamLbl">{T(cf.kr, cf.en)}</span>
							<button class="mItem" onclick={() => stepCost(cf, -1)}>−</button>
							<b class="btParamVal mono">{ctl.btCostsBp[cf.k]}</b>
							<span class="btParamLbl">bp</span>
							<button class="mItem" onclick={() => stepCost(cf, 1)}>+</button>
						</div>
					{/each}
					{#if !costsDefault}<div class="ctRow"><button class="mItem" onclick={() => (ctl.btCostsBp = { ...BT_COSTS })}>{T('비용 기본값', 'reset')}</button></div>{/if}
				{:else}
					<div class="btDesc warn">{T('⚠ 비용 미포함 — 실거래 대비 낙관적', '⚠ costs off — optimistic vs live')}</div>
				{/if}
				<!-- (b) OOS -->
				{#if ctl.btStrategies.length}
					<div class="sdSubLbl">{T('학습/검증 분할 (OOS)', 'train/test split (OOS)')}</div>
					<div class="ctRow ctRowWrap">
						{#each [{ v: 0, kr: '없음', en: 'off' }, { v: 0.7, kr: '70:30', en: '70:30' }, { v: 0.6, kr: '60:40', en: '60:40' }] as o (o.v)}
							<button class={ctl.btOosSplit === o.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.btOosSplit = o.v)}>{T(o.kr, o.en)}</button>
						{/each}
					</div>
					{#if ctl.btOosSplit > 0}<div class="btDesc">{T('파란 구간 = 검증(고정 파라미터 · walk-forward 아님). 검증<학습이면 과최적화 신호', 'blue = out-of-sample (fixed params, not walk-forward); worse = overfit')}</div>{/if}
				{/if}
				<!-- (c) 펀더게이트 안내 -->
				<div class="btDesc">{T('펀더게이트는 ① 전략의 진입 조건으로 추가 · 가격 배경 음영(PIT 공시일 이후)', 'add the fundamental gate as an ENTRY condition · tints the price background (PIT, post-disclosure)')}</div>
			</div>

			<div class="btBench">{T('비교 기준 · 보유(B&H) · 동일 비용', 'benchmark · buy & hold · same costs')}</div>
			<div class="btModelNote">{T('신호 t일 종가 → t+1일 시가 체결 · 미래참조 차단 · 과거 가정 노출형 시뮬레이션(추천 아님)', 'signal close(t) → fill open(t+1) · no look-ahead · not advice')}</div>
		</div>

		<!-- 결과 + 정직 푸터(sticky) — 그래프 금지(equity 는 차트). 결과 없으면 미표시. -->
		{#if pf && ctl.btStrategies.length}
			<HonestyFooter {pf} slots={ctl.btStrategies} focus={ctl.btFocus} withCosts={ctl.btCosts} adjusted={ctl.adj} {lang} onFocus={(i) => ctl.setBtFocus(i)} onOpenReport={onOpenReport ?? (() => {})} />
		{/if}

		<!-- 폭 리사이즈 핸들 — 차트 도크 모드에서만(좌패널 fill 은 컬럼 폭). -->
		{#if !fill}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="sdResize" onpointerdown={startResize} title={T('폭 조절', 'resize')}></div>
		{/if}
	</div>
{/if}

<style>
	.stratDock {
		position: relative;
		flex: none;
		height: 100%;
		display: flex;
		flex-direction: column;
		min-height: 0;
		background: var(--dl-bg-base, #0a0e15);
		border-right: 1px solid var(--dl-line-strong, #2a3142);
		font-family: var(--sans, inherit);
	}
	/* 좌패널 전체 차지 모드 — 컬럼 폭 100%(글로벌 좌측 레일 대체). */
	.stratDock.fill { width: 100%; flex: 1 1 auto; border-right: none; }
	/* 헤더 sticky */
	.sdHeader { flex: none; display: flex; align-items: center; gap: 7px; padding: 6px 8px; border-bottom: 1px solid var(--dl-line-strong, #2a3142); background: rgba(251, 146, 60, 0.05); }
	.sdMark { width: 4px; height: 22px; border-radius: 2px; background: var(--amber, #fb923c); flex: none; }
	.sdTtlWrap { display: flex; flex-direction: column; gap: 1px; flex: 1 1 auto; min-width: 0; }
	.sdTtl { font-size: 12px; font-weight: 700; letter-spacing: 0.04em; color: var(--dl-ink, #c8cfdb); }
	.sdSub { font-size: 10px; color: var(--dim, #8b94a3); }
	.sdHbtn { background: none; border: 1px solid var(--dl-line, #1b2130); color: var(--dim, #8b94a3); cursor: pointer; font-size: 12px; line-height: 1; width: 22px; height: 22px; border-radius: 3px; font-family: inherit; }
	.sdHbtn:hover { color: var(--dl-ink, #c8cfdb); border-color: #3a4456; }
	.sdBody { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 7px; display: flex; flex-direction: column; gap: 4px; }
	.sdCtx { display: flex; align-items: baseline; gap: 5px; font-size: 11px; flex-wrap: wrap; }
	.sdCtxSym { color: var(--dl-ink, #c8cfdb); font-weight: 600; }
	.sdCtxMeta { color: var(--dim, #8b94a3); }
	.sdSubLbl { font-size: 10.5px; color: var(--dim, #8b94a3); margin-top: 5px; }
	.btSection { margin-top: 4px; }
	/* 리사이즈 핸들 */
	.sdResize { position: absolute; top: 0; right: -3px; width: 6px; height: 100%; cursor: col-resize; z-index: 2; }
	.sdResize:hover { background: rgba(251, 146, 60, 0.25); }
	/* 접힘 스파인 */
	.sdSpine { flex: none; width: 28px; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 0; background: var(--dl-bg-base, #0a0e15); border-right: 1px solid var(--dl-line-strong, #2a3142); cursor: pointer; }
	.sdSpine:hover { background: rgba(251, 146, 60, 0.06); }
	.sdSpineTtl { writing-mode: vertical-rl; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--amber, #fb923c); }
	.sdSpineRet { writing-mode: vertical-rl; font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; }

	/* ── 흡수: BtConfig 빌더 스타일(11px floor 유지) ── */
	.ctMenuLbl { font-size: 11px; font-weight: 600; color: #aeb6c2; margin-bottom: 4px; letter-spacing: 0.02em; }
	.ctRow { display: flex; align-items: center; gap: 4px; flex-wrap: nowrap; margin-bottom: 3px; }
	.ctRowWrap { flex-wrap: wrap; }
	.mItem { font-size: 11px; background: var(--dl-bg-raised, #0e141f); color: #aeb6c2; border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 8px; cursor: pointer; font-family: inherit; }
	.mItem:hover { color: var(--dl-ink, #c8cfdb); border-color: #3a4456; }
	.mItem.on { background: var(--amber, #fb923c); color: #1a1206; border-color: var(--amber, #fb923c); font-weight: 600; }
	.btSlot { border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; padding: 5px 6px; margin-bottom: 4px; }
	.btSlot.on { border-color: #2a3142; background: rgba(255, 255, 255, 0.02); }
	.btSlotHd { display: flex; align-items: center; gap: 5px; }
	.btSwBtn { background: none; border: none; padding: 2px; cursor: pointer; display: inline-flex; }
	.btSw { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
	.btSlotLbl { flex: 1 1 auto; min-width: 0; font-size: 11.5px; color: var(--dl-ink, #c8cfdb); display: flex; align-items: center; gap: 5px; }
	.btRuleTag { font-style: normal; font-size: 10px; color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.4); border-radius: 3px; padding: 0 3px; }
	.btSelect { flex: 1 1 auto; min-width: 0; font-size: 11px; background: var(--dl-bg-raised, #0e141f); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 4px; font-family: inherit; }
	.btAdd { width: 100%; margin-top: 2px; }
	.btDel { background: none; border: none; color: var(--dimmer, #5b6573); cursor: pointer; font-size: 12px; padding: 0 3px; }
	.btDel:hover { color: var(--dn, #f0616f); }
	.btParamRow { gap: 3px; }
	.btParamLbl { font-size: 11px; color: #8b94a3; }
	.btParamVal { font-size: 12px; min-width: 30px; text-align: center; color: var(--dl-ink, #c8cfdb); font-variant-numeric: tabular-nums; }
	.btDesc { font-size: 10.5px; color: var(--dim, #8b94a3); line-height: 1.5; margin-top: 3px; }
	.btDesc.warn { color: var(--amber, #fb923c); }
	.btBench { font-size: 10.5px; color: var(--dim, #8b94a3); margin-top: 5px; }
	.btModelNote { font-size: 10px; color: var(--dimmer, #5b6573); line-height: 1.5; margin-top: 2px; }
	.btTfNote { font-size: 11px; color: #fbbf77; background: rgba(251, 146, 60, 0.08); border: 1px solid rgba(251, 146, 60, 0.3); border-radius: 4px; padding: 6px 8px; margin-bottom: 4px; line-height: 1.5; }
	.btTfSwitch { font-size: 10.5px; background: rgba(251, 146, 60, 0.16); border: 1px solid rgba(251, 146, 60, 0.5); color: var(--amber, #fb923c); border-radius: 3px; padding: 1px 8px; cursor: pointer; font-family: inherit; margin-left: 2px; }
	.btTfSwitch:hover { background: rgba(251, 146, 60, 0.26); }
	.btEmpty { padding: 10px; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--dl-line-strong, #2a3142); border-radius: 5px; margin-bottom: 4px; }
	.btEmptyDesc { font-size: 11px; color: #aeb6c2; line-height: 1.6; }
	.condBlk { margin-top: 5px; padding: 5px; border: 1px solid rgba(27, 33, 48, 0.7); border-radius: 4px; }
	.condHd { display: flex; align-items: center; justify-content: space-between; font-size: 11.5px; font-weight: 700; color: #aeb6c2; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 5px; }
	.combineTg { display: flex; gap: 2px; }
	.combineTg button { font-size: 10px; padding: 1px 6px; background: none; border: 1px solid var(--dl-line, #1b2130); color: var(--dimmer, #5b6573); border-radius: 3px; cursor: pointer; font-family: inherit; }
	.combineTg button.on { color: #a78bfa; border-color: rgba(167, 139, 250, 0.5); }
	.condRow { display: flex; align-items: center; gap: 3px; flex-wrap: wrap; margin-bottom: 3px; }
	.condSel, .condOp, .condKind { font-size: 11px; background: var(--dl-bg-raised, #0e141f); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 3px; font-family: inherit; }
	.condOp { min-width: 30px; }
	.condNum { width: 56px; font-size: 11px; background: var(--dl-bg-raised, #0e141f); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 4px; font-variant-numeric: tabular-nums; }
	.condP { display: inline-flex; align-items: center; gap: 1px; }
	.condP button { font-size: 11px; width: 17px; height: 17px; line-height: 1; background: none; border: 1px solid var(--dl-line, #1b2130); color: #aeb6c2; border-radius: 3px; cursor: pointer; padding: 0; }
	.condP b { font-size: 12px; min-width: 22px; text-align: center; font-family: var(--dl-font-mono, monospace); color: var(--dl-ink, #c8cfdb); font-variant-numeric: tabular-nums; }
	.condDel { background: none; border: none; color: var(--dimmer, #5b6573); cursor: pointer; font-size: 11px; padding: 0 2px; }
	.condDel:hover { color: var(--dn, #f0616f); }
	.condAdd { font-size: 10px; background: none; border: 1px dashed var(--dl-line-strong, #2a3142); color: #8b94a3; border-radius: 3px; padding: 3px 8px; cursor: pointer; font-family: inherit; margin-top: 2px; }
	.condAdd:hover { color: var(--dl-ink, #c8cfdb); }
		.sdScope { display: flex; gap: 3px; margin-bottom: 4px; }
	.sdScopeBtn { flex: 1 1 0; font-size: 11px; background: var(--dl-bg-raised, #0e141f); color: #aeb6c2; border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; padding: 4px 0; cursor: pointer; font-family: inherit; }
	.sdScopeBtn.on { background: var(--amber, #fb923c); color: #1a1206; border-color: var(--amber, #fb923c); font-weight: 700; }
	.sdScopeNote { font-size: 10.5px; color: var(--dim, #8b94a3); line-height: 1.5; margin-bottom: 5px; }
	.btPresetGrid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 2px; }
	.btPresetBtn { font-size: 11px; background: rgba(255, 255, 255, 0.03); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; padding: 6px 8px; cursor: pointer; font-family: inherit; text-align: left; }
	.btPresetBtn:hover { border-color: var(--amber, #fb923c); color: var(--amber, #fb923c); }
	.btPresetBtn.rule { border-style: dashed; }
	.btCustomCard { margin-top: 5px; padding: 6px; border: 1px dashed var(--dl-line-strong, #2a3142); border-radius: 4px; display: flex; flex-direction: column; gap: 2px; }
	.btCustomBtn { font-size: 11px; background: none; border: none; color: #a78bfa; cursor: pointer; font-family: inherit; text-align: left; padding: 0; font-weight: 600; }
	.btCustomHint { font-size: 10px; color: var(--dimmer, #5b6573); }
	.tUp { color: var(--up, #34d399); }
	.tDn { color: var(--dn, #f0616f); }
</style>
