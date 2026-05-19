// dartlab 브랜드 토큰 — landing/src/lib/brand.ts 와 동기화 유지.
// 색상은 src/styles/index.css 의 @theme dl-* 변수로도 노출.

export const brand = {
	name: 'DartLab',
	tagline: '종목코드 하나. 기업의 전체 이야기.',
	taglineEn: 'One stock code. Full company story.',
	description: '종목코드 하나로 DART·EDGAR 전자공시를 읽고 비교한다. Python 한 줄.',
	descriptionEn: 'One stock code → structured Korean DART & US SEC EDGAR filings, one line of Python.',
	version: '0.10.0',
	url: 'https://eddmpython.github.io/dartlab/',
	repo: 'https://github.com/eddmpython/dartlab',
	pypi: 'https://pypi.org/project/dartlab/',
	coffee: 'https://buymeacoffee.com/eddmpython',
	desktop: 'https://github.com/eddmpython/dartlab-desktop/releases/latest/download/DartLab.exe',
	colab: 'https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb',
	molab: 'https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py',
	youtube: 'https://www.youtube.com/@eddmpython',
	instagram: 'https://www.instagram.com/dartlab.ai/',
	threads: 'https://www.threads.net/@dartlab.ai',
	author: 'eddmpython',
	hfRepo: 'eddmpython/dartlab-data',
} as const;

export type Brand = typeof brand;
