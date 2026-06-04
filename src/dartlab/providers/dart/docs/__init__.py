"""DART docs 패키지 — ``providers/edgar/docs`` 와 provider 폴더 대칭(folderMirror) 유지 진입 표식.

DART 문서 본문 수집은 gather 계층(``gather.dart``)이, 섹션 파싱·분류는 ``providers/dart/build/
sections`` + ``providers/dart/sectionTopic`` 가 전담한다(docs 농장 은퇴 후 책임 분산). EDGAR 는
``providers/edgar/docs`` 에 집약돼 내부 구조가 다르나, provider 표면 대칭 계약상 본 패키지를 둔다.
"""
