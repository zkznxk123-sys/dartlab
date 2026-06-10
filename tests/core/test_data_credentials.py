"""데이터 공급자 자격증명 레지스트리 회귀 — `core/providers/dataCredentials.py`.

검증:
  1. getKey 우선순위 — 명시 > 환경변수 > SecretStore > None.
  2. resolveKey 미설정 시 레지스트리 기반 안내 CredentialError (envKey·발급 URL 포함).
  3. getSpec 미등록 공급자 가드.
  4. setCredential → SecretStore 라운드트립 (env 부재 시 secret 폴백 해석).
  5. envTemplate / credentialStatus SSOT 불변식 (모든 공급자·envKey 포함).
  6. dataGoKr 단일 키 = gov/customs/pension 3 소스 (공급자 단위 설계 불변식).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

_PROVIDER_ENVS = (
    "DATA_GO_KR_KEY",
    "FRED_API_KEY",
    "ECOS_API_KEY",
    "DART_API_KEY",
    "DART_API_KEYS",
    "KRX_API_KEY",
    "HF_TOKEN",
    "OPENFIGI_API_KEY",
)


@pytest.fixture
def cleanEnv(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """모든 공급자 env 제거 + SecretStore 를 tmp 로 격리."""
    for key in _PROVIDER_ENVS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DARTLAB_HOME", str(tmp_path))
    return tmp_path


def test_getKey_precedence(cleanEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    from dartlab.core.providers.dataCredentials import getKey

    assert getKey("dataGoKr") is None
    assert getKey("dataGoKr", "explicit") == "explicit"
    monkeypatch.setenv("DATA_GO_KR_KEY", "envval")
    assert getKey("dataGoKr") == "envval"
    # 명시 인자가 env 보다 우선
    assert getKey("dataGoKr", "explicit") == "explicit"


def test_resolveKey_missing_guidance(cleanEnv) -> None:
    from dartlab.core.providers.dataCredentials import CredentialError, resolveKey

    with pytest.raises(CredentialError) as exc:
        resolveKey("dataGoKr")
    msg = str(exc.value)
    assert "DATA_GO_KR_KEY" in msg
    assert "data.go.kr" in msg.lower()
    assert "활용신청" in msg


def test_getSpec_unknown_guard() -> None:
    from dartlab.core.providers.dataCredentials import CredentialError, getSpec

    with pytest.raises(CredentialError):
        getSpec("doesNotExist")


def test_setCredential_secret_roundtrip(cleanEnv) -> None:
    from dartlab.core.providers.dataCredentials import getKey, isConfigured, setCredential

    assert not isConfigured("dataGoKr")
    setCredential("dataGoKr", "storedSecret")
    # env 부재인데 secret 에서 해석돼야 한다
    assert getKey("dataGoKr") == "storedSecret"
    assert isConfigured("dataGoKr")


def test_setCredential_rejects_empty(cleanEnv) -> None:
    from dartlab.core.providers.dataCredentials import CredentialError, setCredential

    with pytest.raises(CredentialError):
        setCredential("dataGoKr", "   ")


def test_credentialStatus_source_classification(cleanEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    from dartlab.core.providers.dataCredentials import credentialStatus, setCredential

    monkeypatch.setenv("FRED_API_KEY", "x")
    setCredential("dataGoKr", "y")  # secret
    statuses = {s.id: s for s in credentialStatus()}
    assert statuses["fred"].source == "env"
    assert statuses["dataGoKr"].source == "secret"
    assert statuses["ecos"].source == "missing"
    assert statuses["fred"].configured and not statuses["ecos"].configured


def test_envTemplate_covers_all_providers(cleanEnv) -> None:
    from dartlab.core.providers.dataCredentials import allSpecs, envTemplate

    tmpl = envTemplate()
    for spec in allSpecs():
        assert f"{spec.envKey}=" in tmpl, spec.envKey
        assert spec.signupUrl in tmpl


def test_dataGoKr_single_key_three_sources() -> None:
    from dartlab.core.providers.dataCredentials import getSpec

    spec = getSpec("dataGoKr")
    assert spec.envKey == "DATA_GO_KR_KEY"
    assert set(spec.sources) == {"gov", "customs", "pension"}
