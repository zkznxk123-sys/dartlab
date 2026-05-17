"""Signal — key→numpy boolean array 컨테이너.

Strategy DSL 의 입력 어댑터. 사용자가 quant 축에서 받은 시계열을 boolean 으로
변환해 컨테이너에 넣고, getattr 또는 dict 접근으로 Rule 에 전달.

가중치/스코어 옵션 없음. boolean 만. 점수가 필요하면 사용자가 직접
`(s.a.astype(int) + s.b.astype(int)) > 1` 처럼 명시.

사용 예:
    >>> from dartlab.quant.strategy import Signal
    >>> s = Signal()
    >>> s.add("rsi_oversold", rsi_array < 30)
    >>> s.add("regime_bull", regime_state == 2)
    >>> entry = s.rsi_oversold & s.regime_bull
"""

from __future__ import annotations

import numpy as np


class Signal:
    """Boolean 신호 컨테이너 (numpy bool array 만).

    Strategy DSL 의 진입/청산 컴포지션 단위. 가중치 필드 없음.
    """

    def __init__(self) -> None:
        self._signals: dict[str, np.ndarray] = {}
        self._length: int | None = None

    def add(self, key: str, series) -> "Signal":
        """boolean 또는 boolean-castable array 를 추가.

        길이는 첫 add 기준으로 고정 (이후 add 는 같은 길이만 허용).

        Capabilities:
            - identifier key 검증 + boolean 캐스팅 + 첫 add 기준 길이 lock
            - chained add 지원 (self return)

        Args:
            key: 식별자 (Python identifier).
            series: boolean array 또는 cast 가능 array.

        Returns:
            Signal — self (chaining).

        Guide:
            Strategy DSL 의 진입/청산 컴포지션 단위. ``s.add("up", ema > sma)`` 처럼 chain.

        When:
            Rule 빌드 + AI 조건 합성 답변.

        How:
            identifier 검증 → bool cast → length validate → dict 저장.

        Requires:
            series 가 numpy array 또는 cast 가능.

        Raises:
            ValueError — key 가 invalid identifier 또는 length mismatch.

        Example:
            >>> s = Signal().add("ema_up", ema20 > ema60)
            >>> s.ema_up.dtype
            dtype('bool')

        See Also:
            - Rule : Signal 컴포지션
            - strategy.styles.* : Signal 사용 예

        AIContext:
            DSL 조건 합성 답변 시 add 체인 인용.
        """
        if not key.isidentifier():
            raise ValueError(f"key must be valid identifier: {key!r}")
        arr = np.asarray(series)
        if arr.dtype != np.bool_:
            arr = arr.astype(np.bool_)
        if self._length is None:
            self._length = len(arr)
        elif len(arr) != self._length:
            raise ValueError(f"signal length mismatch: '{key}' has {len(arr)}, expected {self._length}")
        self._signals[key] = arr
        return self

    def __getattr__(self, key: str) -> np.ndarray:
        if key.startswith("_"):
            raise AttributeError(key)
        if key not in self._signals:
            available = list(self._signals.keys())
            raise AttributeError(f"signal {key!r} not added. Available: {available}")
        return self._signals[key]

    def __getitem__(self, key: str) -> np.ndarray:
        if key not in self._signals:
            available = list(self._signals.keys())
            raise KeyError(f"signal {key!r} not added. Available: {available}")
        return self._signals[key]

    def __contains__(self, key: str) -> bool:
        return key in self._signals

    def __len__(self) -> int:
        return self._length or 0

    def keys(self) -> list[str]:
        """등록된 신호 키 목록 반환.

        Returns
        -------
        list[str]
            add() 로 등록된 신호 이름 리스트.

        Example:
            >>> sig.keys()
            ['rsi', 'macd']

        Requires:
            없음.

        Raises:
            없음.
        """
        return list(self._signals.keys())

    def __repr__(self) -> str:
        return f"Signal(keys={list(self._signals.keys())}, length={self._length})"
