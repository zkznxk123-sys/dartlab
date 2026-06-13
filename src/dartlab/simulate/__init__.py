"""simulate — L2.5 scenario driver engine (born-clean foundation).

The simulate engine assembles a deterministic driver DAG over scenario × period coordinates.
Every node is a thin call into an L2 leaf except the single owned macro→fundamentals edge
(`transfer`). This package currently exposes the deterministic foundation only:

- `sheet`: the node contract (`NodeValue` / `DriverNode` / `DriverSheet`) plus the topological
  deterministic executor (`buildOrder` / `evaluateSheet`) and the memoization-key hash
  (`computeInputsHash`).
- `transfer`: the macro→fundamentals edge (`transferMacroToFundamentals` and the horizon carry
  `transferRevenuePath`).

Layer (operation.architecture SSOT): L2.5.
- import OK: dartlab.core (L0), dartlab.gather/providers (L1), dartlab.synth and the other L1.5
  siblings, and the L2 analysis/macro/quant/industry/credit leafs (forward, single-direction).
- not a peer of the L2 analysis engines — calling several L2 leafs from one node is legal.

The public `simulate(...)` verb, driver registry, lens path, and Play are later phases; they are
not exported here.
"""

from __future__ import annotations

from dartlab.simulate.sheet import (
    DriverNode,
    DriverSheet,
    NodeValue,
    buildOrder,
    computeInputsHash,
    evaluateSheet,
)
from dartlab.simulate.transfer import (
    transferMacroToFundamentals,
    transferRevenuePath,
)

__all__ = [
    "NodeValue",
    "DriverNode",
    "DriverSheet",
    "computeInputsHash",
    "buildOrder",
    "evaluateSheet",
    "transferMacroToFundamentals",
    "transferRevenuePath",
]
