# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Instruction
from qiskit.circuit.library import RGate, RXGate, RXXGate, RZGate
from qiskit.circuit.tools import pi_check
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import Target
from qiskit.transpiler.basepasses import BasePass, TransformationPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.passes import Decompose, Optimize1qGatesDecomposition
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin

from qiskit_aqt_provider.utils import map_exceptions


class UnboundParametersTarget(Target):
    """Marker class for transpilation targets to disable passes that require bound parameters."""


def bound_pass_manager() -> PassManager:
    """Transpilation passes to apply on circuits after the parameters are bound.

    This assumes that a preset pass manager was applied to the unbound circuits
    (by setting the target to an instance of `UnboundParametersTarget`).
    """
    return PassManager(
        [
            # wrap the Rxx angles
            WrapRxxAngles(),
            # decompose the substituted Rxx gates
            Decompose([f"{WrapRxxAngles.SUBSTITUTE_GATE_NAME}*"]),
            # collapse the single-qubit gates runs as ZXZ
            Optimize1qGatesDecomposition(basis=["rx", "rz"]),
            # wrap the Rx angles, rewrite as R
            RewriteRxAsR(),
        ]
    )


def rewrite_rx_as_r(theta: float) -> Instruction:
    """Instruction equivalent to Rx(θ) as R(θ, φ) with θ ∈ [0, π] and φ ∈ [0, 2π]."""
    theta = math.atan2(math.sin(theta), math.cos(theta))
    phi = math.pi if theta < 0.0 else 0.0
    return RGate(abs(theta), phi)


class RewriteRxAsR(TransformationPass):
    """Rewrite Rx(θ) and R(θ, φ) as R(θ, φ) with θ ∈ [0, π] and φ ∈ [0, 2π].

    Since the pass needs to determine if the relevant angles are in range,
    target circuits must have all these angles bound when applying the pass.
    """

    @map_exceptions(TranspilerError)
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Apply the transformation pass."""
        for node in dag.gate_nodes():
            if node.name == "rx":
                (theta,) = node.op.params
                dag.substitute_node(node, rewrite_rx_as_r(float(theta)))
        return dag


class AQTSchedulingPlugin(PassManagerStagePlugin):
    """Scheduling stage plugin for the :mod:`qiskit.transpiler`.

    If the transpilation target is not :class:`UnboundParametersTarget`,
    register a single-qubit gates run decomposition and a :class:`RewriteRxAsR` pass,
    irrespective of the optimization level.
    """

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: Optional[int] = None,  # noqa: ARG002
    ) -> PassManager:
        """Pass manager for the scheduling phase."""
        if isinstance(pass_manager_config.target, UnboundParametersTarget):
            return PassManager([])

        passes: list[BasePass] = [
            # The transpilation target defines R/RZ/RXX as basis gates, so the
            # single-qubit gates decomposition pass uses a RR decomposition, which
            # emits code that requires two pulses per single-qubit gates run.
            # Since Z gates are virtual, a ZXZ decomposition is better, because
            # it only requires a single pulse.
            # Apply the single-qubit gates decomposition assuming the basis gates are
            # RX/RZ/RXX, then rewrite RX → R, also wrapping the angles to match
            # the API constraints.
            Optimize1qGatesDecomposition(basis=["rx", "rz"]),
            RewriteRxAsR(),
        ]

        return PassManager(passes)


@dataclass(frozen=True)
class CircuitInstruction:
    """Substitute for `qiskit.circuit.CircuitInstruction`.

    Contrary to its Qiskit counterpart, this type allows
    passing the qubits as integers.
    """

    gate: Gate
    qubits: tuple[int, ...]


def _rxx_positive_angle(theta: float) -> list[CircuitInstruction]:
    """List of instructions equivalent to RXX(θ) with θ >= 0."""
    rxx = CircuitInstruction(RXXGate(abs(theta)), qubits=(0, 1))

    if theta >= 0:
        return [rxx]

    return [
        CircuitInstruction(RZGate(math.pi), (0,)),
        rxx,
        CircuitInstruction(RZGate(math.pi), (0,)),
    ]


def _emit_rxx_instruction(theta: float, instructions: list[CircuitInstruction]) -> Instruction:
    """Collect the passed instructions into a single one labeled 'Rxx(θ)'."""
    qc = QuantumCircuit(2, name=f"{WrapRxxAngles.SUBSTITUTE_GATE_NAME}({pi_check(theta)})")
    for instruction in instructions:
        qc.append(instruction.gate, instruction.qubits)

    return qc.to_instruction()


def wrap_rxx_angle(theta: float) -> Instruction:
    """Instruction equivalent to RXX(θ) with θ ∈ [0, π/2]."""
    # fast path if -π/2 <= θ <= π/2
    if abs(theta) <= math.pi / 2:
        operations = _rxx_positive_angle(theta)
        return _emit_rxx_instruction(theta, operations)

    # exploit 2-pi periodicity of Rxx
    theta %= 2 * math.pi

    if abs(theta) <= math.pi / 2:
        operations = _rxx_positive_angle(theta)
    elif abs(theta) <= 3 * math.pi / 2:
        corrected_angle = theta - np.sign(theta) * math.pi
        operations = [
            CircuitInstruction(RXGate(math.pi), (0,)),
            CircuitInstruction(RXGate(math.pi), (1,)),
        ]
        operations.extend(_rxx_positive_angle(corrected_angle))
    else:
        corrected_angle = theta - np.sign(theta) * 2 * math.pi
        operations = _rxx_positive_angle(corrected_angle)

    return _emit_rxx_instruction(theta, operations)


class WrapRxxAngles(TransformationPass):
    """Wrap Rxx angles to [0, π/2]."""

    SUBSTITUTE_GATE_NAME: Final = "Rxx-wrapped"

    @map_exceptions(TranspilerError)
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Apply the transformation pass."""
        for node in dag.gate_nodes():
            if node.name == "rxx":
                (theta,) = node.op.params

                if 0 <= float(theta) <= math.pi / 2:
                    continue

                rxx = wrap_rxx_angle(float(theta))
                dag.substitute_node(node, rxx)

        return dag


class AQTTranslationPlugin(PassManagerStagePlugin):
    """Translation stage plugin for the :mod:`qiskit.transpiler`.

    If the transpilation target is not :class:`UnboundParametersTarget`,
    register a :class:`WrapRxxAngles` pass after the preset pass irrespective
    of the optimization level.
    """

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: Optional[int] = None,
    ) -> PassManager:
        """Pass manager for the translation stage."""
        translation_pm = common.generate_translation_passmanager(
            target=pass_manager_config.target,
            basis_gates=pass_manager_config.basis_gates,
            approximation_degree=pass_manager_config.approximation_degree,
            coupling_map=pass_manager_config.coupling_map,
            backend_props=pass_manager_config.backend_properties,
            unitary_synthesis_method=pass_manager_config.unitary_synthesis_method,
            unitary_synthesis_plugin_config=pass_manager_config.unitary_synthesis_plugin_config,
            hls_config=pass_manager_config.hls_config,
        )

        if isinstance(pass_manager_config.target, UnboundParametersTarget):
            return translation_pm

        passes: Sequence[BasePass] = [
            WrapRxxAngles(),
        ] + (
            [
                Decompose([f"{WrapRxxAngles.SUBSTITUTE_GATE_NAME}*"]),
            ]
            if optimization_level is None or optimization_level == 0
            else []
        )

        return translation_pm + PassManager(passes)
