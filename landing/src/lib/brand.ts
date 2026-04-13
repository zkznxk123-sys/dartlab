export const brand = {
	name: 'DartLab',
	tagline: '종목코드 하나. 기업의 전체 이야기.',
	taglineEn: 'One stock code. Full company story.',
	description: '종목코드 하나로 DART·EDGAR 공시를 읽고 비교한다. 2,700+ 한국 기업, 970+ 미국 기업, Python 한 줄.',
	descriptionEn: 'One stock code → structured Korean DART & US SEC EDGAR filings. 2,700+ KR, 970+ US companies, one line of Python.',
	version: '0.9.10',
	url: 'https://eddmpython.github.io/dartlab/',
	repo: 'https://github.com/eddmpython/dartlab',
	pypi: 'https://pypi.org/project/dartlab/',
	coffee: 'https://buymeacoffee.com/eddmpython',
	desktop: 'https://github.com/eddmpython/dartlab-desktop/releases/latest/download/DartLab.exe',
	spaces: 'https://huggingface.co/spaces/eddmpython/dartlab',
	colab: 'https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb',
	molab: 'https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py',
	author: 'eddmpython',

	hfRepo: 'eddmpython/dartlab-data',

	data: {
		docs: { dir: 'dart/docs', label: 'DART 공시 문서 데이터' },
		finance: { dir: 'dart/finance', label: '재무 숫자 데이터' },
		report: { dir: 'dart/report', label: '정기보고서 데이터' },
		scan: { dir: 'dart/scan', label: '전종목 횡단분석 프리빌드 데이터' },
		edgarDocs: { dir: 'edgar/docs', label: 'SEC EDGAR 공시 문서 데이터' },
		edgar: { dir: 'edgar/finance', label: 'SEC EDGAR 재무 데이터' },
	},

	color: {
		primary: '#ea4647',
		primaryDark: '#c83232',
		primaryLight: '#f87171',
		accent: '#fb923c',
		accentLight: '#fdba74',
		bgDark: '#050811',
		bgDarker: '#030509',
		bgCard: '#0f1219',
		bgCardHover: '#1a1f2b',
		text: '#f1f5f9',
		textMuted: '#94a3b8',
		textDim: '#64748b',
		border: '#1e2433',
		success: '#34d399',
		warning: '#fbbf24',
		coffee: '#ffdd00'
	}
} as const;

export type Brand = typeof brand;
