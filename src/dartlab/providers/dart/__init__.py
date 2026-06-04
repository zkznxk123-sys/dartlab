"""DART 데이터 소스 엔진."""

# docs 농장 은퇴 — eager import 제거 (panel 이 공시 표면). finance/report survivor 만 로드.
from dartlab.providers.dart import finance, report
from dartlab.providers.dart.company import Company

# DART fetch(키 포함)는 gather 전담 (ETL Extract). DartKeyProvider(CredentialProvider)
# 등록은 core.credentials 가 gather.dart.keys 발견으로 트리거 — providers↛gather 유지.

__all__ = [
    "finance",
    "report",
    "Company",
]
