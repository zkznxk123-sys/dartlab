// 브라우저: HF panel parquet 하나 직접 read → PanelBundle (와이드 빌드 0, 온더플라이).
// 순수 코어 `buildPanelBundle`(panelWide.ts)와 분리 — IO 만 담당(테스트는 코어 단독).

import { readParquetRows } from '$lib/data/hfRange';
import { marketForCode } from './dartUrl';
import { buildPanelBundle } from './panelWide';
import type { LeafRow, PanelBundle } from './types';
import noteTaxonomy from './noteTaxonomy.json';

export const READ_COLUMNS = [
	'chapter', 'sectionLeaf', 'sectionPath', 'blockLeaf', 'leafType',
	'disclosureKey', 'xbrlClass', 'blockOrder', 'contentRaw', 'period', 'rceptNo'
];

export async function loadPanelBundle(code: string, opts: { corpName?: string } = {}): Promise<PanelBundle> {
	const base = marketForCode(code) === 'US' ? 'edgar' : 'dart';
	const path = `${base}/panel/${code}.parquet`;
	const { rows } = await readParquetRows(path, { columns: READ_COLUMNS });
	return buildPanelBundle(rows as unknown as LeafRow[], {
		code,
		corpName: opts.corpName,
		noteTaxonomy: noteTaxonomy as Record<string, string>
	});
}
