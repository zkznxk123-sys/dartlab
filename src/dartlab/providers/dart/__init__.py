"""DART 데이터 소스 엔진."""

from dartlab.providers.dart import docs, finance, report
from dartlab.providers.dart.company import Company

# dartKey 모듈은 module load 시점에 CredentialProvider 를 register (정공법 B — DIP).
# 가볍기 때문에 (dataclass + 함수) eager import 안전.
from dartlab.providers.dart.openapi import dartKey as _dartKey  # noqa: F401

__all__ = [
    "finance",
    "report",
    "docs",
    "Company",
]
