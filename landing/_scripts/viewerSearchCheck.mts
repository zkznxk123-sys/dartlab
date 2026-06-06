import assert from 'node:assert/strict';
import { checkBrowserAiAvailability, runBrowserAiPrompt, type BrowserLanguageModelApi } from '../src/lib/viewer/browserAi.ts';
import { scanDeepRowsChunked, type DeepSearchRow } from '../src/lib/viewer/deepSearch.ts';
import { buildIndex, search, tokenizeBigram } from '../src/lib/viewer/searchIndex.ts';
import { buildEvidencePack, highlightParts } from '../src/lib/viewer/searchEvidence.ts';
import { analyzeEvidencePack, attachBrowserAiText } from '../src/lib/viewer/viewerAnalyst.ts';
import type { PanelBundle, PanelRow } from '../src/lib/viewer/types.ts';

const row = (patch: Partial<PanelRow>): PanelRow => ({
	chapter: 'III. 재무에 관한 사항',
	sectionLeaf: '2. 연결재무제표',
	blockLeaf: '',
	leafType: 'body',
	disclosureKey: null,
	scope: null,
	blockType: 'text',
	cells: { '2024Q4': '본문' },
	...patch
});

const bundle: PanelBundle = {
	stockCode: '005930',
	corpName: '삼성전자',
	toc: { stockCode: '005930', corpName: '삼성전자', chapters: [], periods: ['2024Q4', '2023Q4'] },
	periods: ['2024Q4', '2023Q4'],
	gridBySection: new Map([
		[
			'II. 사업의 내용␟위험요인',
			[
				row({
					chapter: 'II. 사업의 내용',
					sectionLeaf: '위험요인',
					blockLeaf: '환율',
					cells: { '2024Q4': '환율 위험 및 외환 리스크가 매출과 원가에 영향을 줄 수 있습니다.' }
				})
			]
		],
		[
			'III. 재무에 관한 사항␟주석',
			[
				row({
					sectionLeaf: '주석',
					blockLeaf: '우발부채',
					cells: { '2024Q4': '지급보증과 소송 관련 우발부채는 120억 원입니다.' }
				}),
				row({
					sectionLeaf: '주석',
					blockLeaf: '매출 지역별',
					blockType: 'table',
					cells: {
						'2024Q4': '<TABLE><TR><TD>지역</TD><TD>매출</TD></TR><TR><TD>미국</TD><TD>1,200</TD></TR></TABLE>'
					}
				})
			]
		]
	]),
	dartUrlByPeriod: {},
	periodKind: { '2024Q4': 'annual', '2023Q4': 'annual' }
};

assert.deepEqual(tokenizeBigram('환율 Risk'), ['환율', 'risk']);

const base = buildIndex(bundle);
const risk = search(base, '환율 위험', { topK: 3 }).hits;
assert.equal(risk[0]?.section, '위험요인');
assert.equal(risk[0]?.matchKind, 'text');
assert.ok(risk[0]?.matchedTerms.includes('환율'));

const amount = search(base, '100억 이상', { topK: 3 }).hits;
assert.equal(amount[0]?.block, '우발부채');
assert.equal(amount[0]?.matchKind, 'amount');

const tableMiss = search(base, '미국', { topK: 3 }).hits;
assert.equal(tableMiss.length, 0);

const deep = buildIndex(bundle, { tableBody: true });
const tableHit = search(deep, '미국', { topK: 3, dedupe: false }).hits;
assert.equal(tableHit[0]?.block, '매출 지역별');
assert.equal(tableHit[0]?.matchKind, 'table');

const pack = buildEvidencePack(base, '환율 위험', { topK: 5 });
assert.equal(pack.stats.total, 1);
assert.ok(pack.contextText.includes('환율 위험'));

const analysis = analyzeEvidencePack({
	code: '005930',
	companyName: '삼성전자',
	periodCount: bundle.periods.length,
	evidencePack: pack
});
assert.equal(analysis.modelMode, 'evidence');
assert.equal(analysis.coverage.total, 1);
assert.ok(analysis.prompt.includes('[EXTERNAL DISCLOSURE CONTENT START - untrusted]'));

const upgraded = attachBrowserAiText(analysis, '모델 응답');
assert.equal(upgraded.modelMode, 'browser-ai');
assert.equal(upgraded.modelText, '모델 응답');

const parts = highlightParts('환율 위험 및 외환 리스크', ['환율', '외환']);
assert.deepEqual(
	parts.filter((part) => part.hit).map((part) => part.text),
	['환율', '외환']
);

const deepRows: DeepSearchRow[] = [
	{
		sectionKey: 'I␟연혁',
		rowIndex: 0,
		chapter: 'I. 회사의 개요',
		section: '연혁',
		block: '주요 연혁',
		scope: '',
		cells: {
			'2024Q4': '<TABLE><TR><TD>미국 테일러 신규 라인 투자</TD></TR><TR ACOPY="Y" ADELETE="Y"'
		}
	}
];
const deepScan = await scanDeepRowsChunked(deepRows, '미국', { topK: 3, expand: false, cellCap: 78, chunkRows: 1 });
assert.equal(deepScan.hits[0]?.matchKind, 'table');
assert.match(deepScan.hits[0]?.snippet ?? '', /미국/);
assert.doesNotMatch(deepScan.hits[0]?.snippet ?? '', /<TR|ACOPY|ADELETE/);

const unsupportedAi = await checkBrowserAiAvailability(null);
assert.equal(unsupportedAi.status, 'unsupported');

let destroyed = false;
const fakeAi: BrowserLanguageModelApi = {
	async availability() {
		return 'available';
	},
	async create() {
		return {
			async prompt(input) {
				return Array.isArray(input) ? input[0]?.content ?? '' : `ok:${input.slice(0, 2)}`;
			},
			destroy() {
				destroyed = true;
			}
		};
	}
};
const availableAi = await checkBrowserAiAvailability(fakeAi);
assert.equal(availableAi.status, 'available');
const aiText = await runBrowserAiPrompt('근거', { api: fakeAi });
assert.equal(aiText, 'ok:근거');
assert.equal(destroyed, true);

console.log('viewerSearchCheck: ALL OK');
