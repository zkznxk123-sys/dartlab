// 공시뷰어 readWide 포팅 순수단위 검증 (데이터 불필요). Python canonicalChapterExpr / _viewerUrlForFiling 대조.
// 실행: cd landing && npx tsx _scripts/viewerCheck.mts
// (전체 parity = data/dart/panel 로컬 필요, 별도 수동 — 본 스크립트는 결정론 순수함수만.)
import { canonicalChapter } from '../src/lib/viewer/canonical.ts';
import { viewerUrl, marketForCode } from '../src/lib/viewer/dartUrl.ts';

let fail = 0;
const eq = (got: unknown, exp: unknown, label: string) => {
	if (JSON.stringify(got) !== JSON.stringify(exp)) { fail++; console.log('FAIL', label, '\n  got', JSON.stringify(got), '\n  exp', JSON.stringify(exp)); }
};

// canonicalChapter — 붕괴 II→III 복원·(첨부)→III·depth V·honest fallback (Python 대조값).
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용␟III. 재무에 관한 사항'), 'III. 재무에 관한 사항', 'collapse II→III');
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용'), 'II. 사업의 내용', 'no-collapse II');
eq(canonicalChapter('III. 재무에 관한 사항', '(첨부)재무제표'), 'III. 재무에 관한 사항', '(첨부)→III');
eq(canonicalChapter('별난 챕터', '별난 챕터'), '별난 챕터', 'honest fallback');
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용␟V. 회계감사인의 감사의견 등␟외부감사'), 'V. 회계감사인의 감사의견 등', 'depth V');

// viewerUrl — KR DART(rcpNo) / US SEC(filing index, cik=accession 앞10자리).
eq(viewerUrl(marketForCode('005930'), '20260515002181'), 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002181', 'KR DART');
eq(viewerUrl(marketForCode('AAPL'), '0000320193-25-000079'), 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm', 'US SEC');
eq(viewerUrl('US', null), null, 'US null');

console.log(fail === 0 ? 'viewerCheck: ALL OK (8/8)' : `viewerCheck: ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);
