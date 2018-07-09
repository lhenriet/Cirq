# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Basic types defining qubits, gates, and operations."""

from typing import Sequence, FrozenSet, Tuple, Union, TYPE_CHECKING, cast

from cirq import extension
from cirq.ops import raw_types, gate_features

if TYPE_CHECKING:
    # pylint: disable=unused-import
    from typing import Dict, List


LIFTED_POTENTIAL_TYPES = [
    gate_features.ReversibleEffect,
    gate_features.ExtrapolatableEffect
]


class GateOperation(raw_types.Operation,
                    extension.PotentialImplementation):
    """An application of a gate to a collection of qubits.

    Attributes:
        gate: The applied gate.
        qubits: A sequence of the qubits on which the gate is applied.
    """

    def __init__(self,
                 gate: raw_types.Gate,
                 qubits: Sequence[raw_types.QubitId]) -> None:
        self._gate = gate
        self._qubits = tuple(qubits)

    @property
    def gate(self) -> raw_types.Gate:
        return self._gate

    @property
    def qubits(self) -> Tuple[raw_types.QubitId, ...]:
        return self._qubits

    def with_qubits(self, *new_qubits: raw_types.QubitId) -> 'GateOperation':
        return self.gate.on(*new_qubits)

    def with_gate(self, new_gate: raw_types.Gate) -> 'GateOperation':
        return new_gate.on(*self.qubits)

    def __repr__(self):
        return 'GateOperation({!r}, {!r})'.format(self.gate, self.qubits)

    def __str__(self):
        return '{}({})'.format(self.gate,
                               ', '.join(str(e) for e in self.qubits))

    def _group_interchangeable_qubits(self) -> Tuple[
            Union[raw_types.QubitId,
                  Tuple[int, FrozenSet[raw_types.QubitId]]],
            ...]:

        cast_gate = extension.try_cast(gate_features.InterchangeableQubitsGate,
                                       self.gate)
        if cast_gate is None:
            return self.qubits

        groups = {}  # type: Dict[int, List[raw_types.QubitId]]
        for i, q in enumerate(self.qubits):
            k = cast_gate.qubit_index_to_equivalence_group_key(i)
            if k not in groups:
                groups[k] = []
            groups[k].append(q)
        return tuple(sorted((k, frozenset(v)) for k, v in groups.items()))

    def _eq_tuple(self):
        grouped_qubits = self._group_interchangeable_qubits()
        return raw_types.Operation, self.gate, grouped_qubits

    def __hash__(self):
        return hash(self._eq_tuple())

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._eq_tuple() == other._eq_tuple()

    def __ne__(self, other):
        return not self == other

    def try_cast_to(self, desired_type, extensions):
        if desired_type in LIFTED_POTENTIAL_TYPES:
            cast_gate = extensions.try_cast(desired_type, self.gate)
            if cast_gate is not None:
                return self.with_gate(cast_gate)
        return None

    def inverse(self) -> 'GateOperation':
        cast_gate = extension.cast(gate_features.ReversibleEffect, self.gate)
        return self.with_gate(cast(raw_types.Gate, cast_gate.inverse()))

    def extrapolate_effect(self, factor: float) -> 'GateOperation':
        cast_gate = extension.cast(gate_features.ExtrapolatableEffect,
                                   self.gate)
        return self.with_gate(cast(raw_types.Gate,
                                   cast_gate.extrapolate_effect(factor)))

    def __pow__(self, power: float) -> 'GateOperation':
        """Raise gate to a power, then reapply to the same qubits.

        Only works if the gate implements cirq.ExtrapolatableEffect.
        For extrapolatable gate G this means the following two are equivalent:

            (G ** 1.5)(qubit)  or  G(qubit) ** 1.5

        Args:
            power: The amount to scale the gate's effect by.

        Returns:
            A new operation on the same qubits with the scaled gate.
        """
        return self.extrapolate_effect(power)