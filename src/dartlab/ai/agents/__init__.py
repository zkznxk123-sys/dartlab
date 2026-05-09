"""Agent loops — provider-driven ReAct over the 6 workbench tools.

`runToolLoop` 은 어떤 LLMProvider 가 와도 같은 도구 화이트리스트로 분석을
밀어붙인다. 작업대 패스 (brief/work/critique/compose) 가 본 모듈을 호출해
도구 자율 조합을 수행한다.
"""

from .runToolLoop import AgentResult, runToolLoop

__all__ = ["AgentResult", "runToolLoop"]
