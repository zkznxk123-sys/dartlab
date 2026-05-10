"""Provider 설정 안내 문구 SSOT (core 강등).

이전: src/dartlab/ai/settings/aiSetup.py 의 데이터·포매팅 부분 (0.10 까지 shim 유지).
사유: 안내 문구 데이터·포매팅은 cross-cutting (messaging·CLI·서버 모두 사용).
provider 가용성 체크 (`_check_provider_available`) 와 status 테이블은
ai.providers 의존이라 ai/settings/aiSetup.py 에 잔존.
"""

from __future__ import annotations

_PROVIDER_ALIAS: dict[str, str] = {
    "chatgpt": "oauth-codex",
    "gpt": "oauth-codex",
    "google": "gemini",
}

_SETUP_GUIDES: dict[str, dict[str, str]] = {
    "gemini": {
        "name": "Google Gemini (무료)",
        "short": "Gemini 2.5 Pro/Flash 무료",
        "setup_notebook": 'dartlab.setup("gemini")',
        "setup_cli": "dartlab setup gemini",
        "detail": ("Google AI Studio에서 무료 API 키를 발급받으세요.\nhttps://aistudio.google.com/apikey"),
    },
    "groq": {
        "name": "Groq (무료)",
        "short": "초고속 추론 — LLaMA 3.3 70B 무료",
        "setup_notebook": 'dartlab.setup("groq")',
        "setup_cli": "dartlab setup groq",
        "detail": ("Groq Cloud에서 무료 API 키를 발급받으세요.\nhttps://console.groq.com/keys"),
    },
    "cerebras": {
        "name": "Cerebras (무료)",
        "short": "1M tokens/day 영구 무료",
        "setup_notebook": 'dartlab.setup("cerebras")',
        "setup_cli": "dartlab setup cerebras",
        "detail": ("Cerebras Inference에서 무료 API 키를 발급받으세요.\nhttps://cloud.cerebras.ai/"),
    },
    "mistral": {
        "name": "Mistral AI (무료)",
        "short": "1B tokens/month 무료, 다양한 모델",
        "setup_notebook": 'dartlab.setup("mistral")',
        "setup_cli": "dartlab setup mistral",
        "detail": ("Mistral AI에서 무료 API 키를 발급받으세요.\nhttps://console.mistral.ai/api-keys"),
    },
    "oauth-codex": {
        "name": "ChatGPT 구독 계정",
        "short": "브라우저 로그인 (ChatGPT Plus/Pro)",
        "setup_notebook": 'dartlab.setup("chatgpt")',
        "setup_cli": "dartlab setup oauth-codex",
        "detail": (
            "ChatGPT Plus 또는 Pro 구독자는 API 키 없이 사용할 수 있습니다.\n"
            "브라우저에서 ChatGPT 계정으로 로그인하면 자동 인증됩니다."
        ),
    },
    "openai": {
        "name": "OpenAI API",
        "short": "API 키 필요 (최신 GPT/Reasoning 모델)",
        "setup_notebook": 'dartlab.llm.configure(provider="openai", api_key="sk-...")',
        "setup_cli": "dartlab setup openai",
        "detail": ("OpenAI API 키가 필요합니다.\nhttps://platform.openai.com/api-keys 에서 발급받으세요."),
    },
    "ollama": {
        "name": "로컬 LLM (무료)",
        "short": "오프라인, 프라이빗 — 설치 필요",
        "setup_notebook": 'dartlab.setup("ollama")',
        "setup_cli": "dartlab setup ollama",
        "detail": (
            "무료, 오프라인으로 사용 가능한 로컬 LLM입니다.\n"
            "https://ollama.com/download 에서 설치 후 `ollama serve` 실행."
        ),
    },
    "codex": {
        "name": "Codex CLI",
        "short": "코딩 에이전트용",
        "setup_notebook": 'dartlab.setup("codex")',
        "setup_cli": "dartlab setup codex",
        "detail": ("코딩 에이전트 전용 provider입니다.\n`npm install -g @openai/codex` 설치 후 `codex login`."),
    },
}

DISPLAY_ORDER: tuple[str, ...] = ("gemini", "groq", "cerebras", "mistral", "oauth-codex", "openai", "ollama", "codex")


def resolveAlias(provider: str) -> str:
    """사용자 편의 alias 를 정식 provider id 로 변환."""
    return _PROVIDER_ALIAS.get(provider.lower(), provider)


def providerGuide(provider: str) -> str:
    """특정 provider 의 설정 안내 문자열 반환."""
    provider = resolveAlias(provider)
    guide = _SETUP_GUIDES.get(provider)
    if guide is None:
        return f"  알 수 없는 provider: {provider}"
    detailLines = "\n".join(f"  {line}" for line in guide["detail"].split("\n"))
    lines = [
        f"  [ {guide['name']} ]",
        "",
        detailLines,
        "",
        f"  노트북:  {guide['setup_notebook']}",
        f"  CLI:     {guide['setup_cli']}",
    ]
    return "\n".join(lines)


def noProviderMessage() -> str:
    """Provider 미설정 시 표시할 안내 메시지 반환."""
    lines = [
        "",
        "  AI provider가 설정되지 않았습니다.",
        "",
        "  무료 API 키 하나면 바로 시작할 수 있습니다:",
        "",
        '  1. Gemini (권장)   — dartlab.setup("gemini")    https://aistudio.google.com/apikey',
        '  2. Groq            — dartlab.setup("groq")      https://console.groq.com/keys',
        '  3. Cerebras        — dartlab.setup("cerebras")  https://cloud.cerebras.ai/',
        '  4. Mistral         — dartlab.setup("mistral")   https://console.mistral.ai/api-keys',
        "",
        "  기타:",
        '  5. ChatGPT (구독)  — dartlab.setup("chatgpt")',
        '  6. OpenAI API      — dartlab.setup("openai")',
        '  7. 로컬 LLM        — dartlab.setup("ollama")',
        "",
        "  설정 후 다시 실행하세요:",
        '     dartlab.ask("삼성전자 재무건전성 분석해줘")',
        "",
    ]
    return "\n".join(lines)
