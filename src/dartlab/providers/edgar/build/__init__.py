"""EDGAR build 패키지 — ``providers/dart/build`` 의 폴더 대칭(folderMirror) 미러.

EDGAR 빌드 seam(``EdgarBuildProvider`` 등록 · panel 빌드 진입)은 ``providers/edgar/buildSeam``
모듈이 전담한다. 본 패키지는 그 seam 을 재노출(import 시 등록 트리거 보존)해 dart/build 와
provider 폴더 구조를 대칭으로 유지한다 — 빌드 로직 본체는 buildSeam 에 그대로 둔다.
"""

from dartlab.providers.edgar import buildSeam  # noqa: F401  (build seam 재노출 + EdgarBuildProvider 등록 트리거)
