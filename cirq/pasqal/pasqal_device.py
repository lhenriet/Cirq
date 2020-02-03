from typing import FrozenSet, Iterable, cast
from numpy import sqrt

import cirq

from cirq.pasqal import ThreeDGridQubit


class PasqalDevice(cirq.neutral_atoms.NeutralAtomDevice):

    def __init__(self, control_radius: float,
                 qubits: Iterable[ThreeDGridQubit]) -> None:

        us = 1000 * cirq.value.Duration(nanos=1)

        self._measurement_duration = 5000 * us
        self._gate_duration = 2 * us
        self._max_parallel_z = 2
        self._max_parallel_xy = 2
        self._max_parallel_c = 10
        self._max_parallel_t = 1

        for q in qubits:
            if not isinstance(q, ThreeDGridQubit):
                raise TypeError('Unsupported qubit type: {!r}'.format(q))

        if not control_radius >= 0:
            raise ValueError("control_radius needs to be a non-negative float")

        self.control_radius = control_radius

        self.qubits = qubits

    def qubit_set(self) -> FrozenSet[cirq.Qid]:
        return frozenset(self.qubits)

    def qubit_list(self):
        return [qubit for qubit in self.qubit_set()]

    def decompose_operation(self, operation: cirq.ops.Operation) -> 'cirq.OP_TREE':

        decomposition = [operation]

        if not isinstance(operation, cirq.ops.GateOperation):
            raise TypeError("{!r} is not a gate operation.".format(operation))

        # default value

        """
            Try to decompose the operation into elementary device operations
            TODO: Test how this works for different circuits
        """
        if not PasqalDevice.is_pasqal_device_op(operation):
            decomposition = cirq.protocols.decompose(operation,
                                           keep=PasqalDevice.is_pasqal_device_op)

        for dec in decomposition:
            if not PasqalDevice.is_pasqal_device_op(dec):
                raise TypeError("Don't know how to work with {!r}.".format(
                    operation.gate))

        return decomposition

    @staticmethod
    def is_pasqal_device_op(op: cirq.ops.Operation) -> bool:
        if not isinstance(op, cirq.ops.GateOperation):
            return False

        keep = False

        #Currently accepting all multi-qubit operations
        keep = keep or (len(op.qubits) > 1)

        keep = keep or (isinstance(op.gate, cirq.ops.YPowGate))

        keep = keep or (isinstance(op.gate, cirq.ops.ZPowGate))

        keep = keep or (isinstance(op.gate, cirq.ops.XPowGate))

        keep = keep or (isinstance(op.gate, cirq.ops.PhasedXPowGate))

        keep = keep or (isinstance(op.gate, cirq.ops.MeasurementGate))

        keep = keep or (isinstance(op.gate, cirq.ops.IdentityGate))

        return keep

    def validate_operation(self, operation: cirq.ops.Operation):
        if not isinstance(operation, cirq.GateOperation):
            raise ValueError('{!r} is not a supported '
                             'operation'.format(operation))

        if not PasqalDevice.is_pasqal_device_op(operation):
            raise ValueError('{!r} is not a supported '
                             'gate'.format(operation.gate))

        for qub in operation.qubits:
            if not isinstance(qub, ThreeDGridQubit):
                raise ValueError('{} is not a 3D grid qubit '
                                 'for gate {!r}'.format(qub, operation.gate))

        if isinstance(operation.gate, (cirq.ops.MeasurementGate, cirq.ops.IdentityGate)):
            return

        # Verify that a controlled gate operation is valid
        if isinstance(operation, cirq.ops.GateOperation):
            if len(operation.qubits) > self._max_parallel_c + self._max_parallel_t:
                raise ValueError("Too many qubits acted on in parallel by a"
                                 "controlled gate operation")
            if len(operation.qubits) > 1:
                for p in operation.qubits:
                    for q in operation.qubits:
                        if self.distance(p, q) > self.control_radius:
                            raise ValueError("Qubits {!r}, {!r} are too "
                                             "far away".format(p, q))

        # Verify that a valid number of Z gates are applied in parallel
        if isinstance(operation.gate, cirq.ops.ZPowGate):
            if len(operation.qubits) > self._max_parallel_z:
                raise ValueError("Too many Z gates in parallel")

        # Verify that a valid number of XY gates are applied in parallel
        if isinstance(operation.gate,
                      (cirq.ops.XPowGate, cirq.ops.YPowGate, cirq.ops.PhasedXPowGate)):
            if (len(operation.qubits) > self._max_parallel_xy and
                    len(operation.qubits) != len(self.qubit_list())):
                raise ValueError("Bad number of X/Y gates in parallel")

    def distance(self, p: 'cirq.Qid', q: 'cirq.Qid') -> float:
        if not isinstance(q, ThreeDGridQubit):
            raise ValueError('Unsupported qubit type: {!r}'.format(q))
        if not isinstance(p, ThreeDGridQubit):
            raise ValueError('Unsupported qubit type: {!r}'.format(p))
        p = cast(ThreeDGridQubit, p)
        q = cast(ThreeDGridQubit, q)
        return sqrt((p.row - q.row) ** 2 + (p.col - q.col) ** 2 +
                    (p.lay - q.lay) ** 2)

    def __repr__(self):
        return ('pasqal.PasqalDevice(control_radius={!r}, '
                'qubits={!r})').format(self.control_radius,
                                       sorted(self.qubits))

    def _value_equality_values_(self):
        return (self._measurement_duration,
                self._gate_duration,
                self._max_parallel_z,
                self._max_parallel_xy,
                self._max_parallel_c,
                self.control_radius,
                self.qubits)

    def _json_dict_(self):
        return cirq.protocols.obj_to_dict_helper(self, ['control_radius',
                                                        'qubits'
                                                        ])
