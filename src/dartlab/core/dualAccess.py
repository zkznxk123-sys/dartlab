"""dual access pattern — single 진입점에 call form + attr form 둘 다 허용.

``operation.apiContract`` 의 "단일 진입점 + 파라미터 계약" 사상은 진입점을 늘리는
것이 아니라 같은 진입점에서 두 가지 access form 을 모두 허용한다는 의미.
pandas 가 ``df["col"]`` 와 ``df.col`` 둘 다 허용하는 것과 같다.

dartlab 의 모든 사용자 진입점 (Company.show / select / analysis / credit / story,
dartlab.scan / macro / quant / gather) 은 같은 패턴:

    엔진("축", ...)         # call form (canonical)
    엔진.축                  # attr form (returns bound callable)
    엔진.축()                # attr → call
    엔진.축(target=...)      # attr → call with kwargs

``CallableAccessor`` 는 이 패턴의 단일 진실의 원천 구현이다.
"""

from __future__ import annotations

from typing import Any, Callable


class CallableAccessor:
    """Dual access wrapper — call form + attribute form 양쪽 지원.

    Examples:
        >>> def myShow(topic, *, freq="Q"):
        ...     return f"{topic}/{freq}"
        >>> show = CallableAccessor(myShow)
        >>> show("IS")
        'IS/Q'
        >>> show.IS()
        'IS/Q'
        >>> show.IS(freq="Y")
        'IS/Y'

    Notes:
        - ``__getattr__`` 는 첫 인자를 attr 이름으로 바인드한 callable 반환
        - ``_`` 로 시작하는 dunder/private 이름은 일반 attribute lookup 위임
        - 호출 결과를 캐싱하지 않음 — caller 가 결정
    """

    __slots__ = ("_fn", "_name")

    def __init__(self, fn: Callable[..., Any], *, name: str | None = None):
        self._fn = fn
        self._name = name or getattr(fn, "__name__", "callable")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)

    def __getattr__(self, attr: str) -> Callable[..., Any]:
        if attr.startswith("_"):
            raise AttributeError(attr)

        fn = self._fn

        def bound(*args: Any, **kwargs: Any) -> Any:
            """attribute 이름을 첫 인자로 고정해 원 함수 호출.

            Requires:
                감싼 함수가 ``fn(attr, *args, **kwargs)`` 호출 형태를 받아야 한다.
            Raises:
                원 함수가 발생시키는 예외를 그대로 전달한다.
            Args:
                *args: attr 뒤에 전달할 위치 인자.
                **kwargs: 원 함수에 전달할 키워드 인자.
            Returns:
                원 함수가 반환한 값을 그대로 반환한다.
            Example:
                >>> def pick(topic):
                ...     return topic
                >>> CallableAccessor(pick).BS()
                'BS'
            """
            return fn(attr, *args, **kwargs)

        bound.__name__ = attr
        bound.__doc__ = f"{self._name}({attr!r}, ...)"
        return bound

    def __repr__(self) -> str:
        return f"<CallableAccessor {self._name}>"
