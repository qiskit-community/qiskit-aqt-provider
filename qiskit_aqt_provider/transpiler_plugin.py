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
"""AQT transpiler plugin.

The transpilation for AQT backends is based on
[custom plugins](https://quantum.cloud.ibm.com/docs/en/api/qiskit/transpiler_plugins#writing-plugins)
that are connected to the AQT resources/backends with
[custom transpiler passes](https://quantum.cloud.ibm.com/docs/en/api/qiskit/providers#custom-transpiler-passes)
for backends. There are two transpilation stages that can be customized this way:
- Translation stage:
  - Wrapping RXX gate angles before the optimization stage so the optimization can do its thing.
  - If optimization level is 0, decomposing the RXX wrapped gates (the ones with the substituted
    name), as the optimization stage will not take care of it.
- Scheduling stage:
  - Decomposing single-qubit gates
  - Rewriting RX → R, also wrapping the angles
  - Wrapping RXX gate angles again. Due to optimization there may be incompatible angles again
  - Decomposing wrapped RXX gates
  - Remove redundant final measurements and raise error for mid-circuit measurements
"""

import math
from dataclasses import dataclass
from typing import Final, Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Gate, Instruction
from qiskit.circuit.library import RGate, RXGate, RXXGate, RZGate
from qiskit.circuit.tools import pi_check
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.passes import Decompose, Optimize1qGatesDecomposition
from qiskit.transpiler.passmanager import PassManager, Task
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin

from qiskit_aqt_provider.utils import map_exceptions


def _rewrite_rx_as_r(theta: float) -> Instruction:
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
                dag.substitute_node(node, _rewrite_rx_as_r(float(theta)))
        return dag


class EnsureSingleFinalMeasurement(TransformationPass):
    """Ensure at most one measurement per qubit, only at the end of the circuit."""

    @map_exceptions(TranspilerError)
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Ensures exactly one measurement at the end of the circuit.

        Some algorithms introduce measurements. If they are at the end of the circuit, they can be
        safely replaced by a single measure all operation. This pass ensures that there is exactly
        one measurement at the end of the circuit, and raises a TranspilerError if it finds a
        mid-circuit measurement.
        """
        ops = list(dag.topological_op_nodes())

        if not ops:
            return dag

        seen_measure = False
        measured_qubits = set()

        # We will rebuild a filtered DAG
        new_dag = DAGCircuit()
        new_dag.name = dag.name
        new_dag.metadata = dag.metadata.copy() if dag.metadata else {}
        new_dag.global_phase = dag.global_phase

        # Copy over registers
        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        for node in ops:
            op_name = node.op.name

            if op_name == "measure":
                q = node.qargs[0]

                # drop duplicate measurements
                if q in measured_qubits:
                    continue

                measured_qubits.add(q)
                seen_measure = True

                new_dag.apply_operation_back(
                    node.op,
                    node.qargs,
                    node.cargs,
                )

            elif op_name == "barrier":
                # drop barriers after measurement starts
                if seen_measure:
                    continue

                new_dag.apply_operation_back(
                    node.op,
                    node.qargs,
                    node.cargs,
                )

            else:
                if seen_measure:
                    raise TranspilerError(
                        "Measurement must only occur at the end of the circuit "
                        "(found non-measure operation after measurement)."
                    )

                new_dag.apply_operation_back(
                    node.op,
                    node.qargs,
                    node.cargs,
                )

        return new_dag


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


def _wrap_rxx_angle(theta: float) -> Instruction:
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

                rxx = _wrap_rxx_angle(float(theta))
                dag.substitute_node(node, rxx)

        return dag


class AQTTranslationPlugin(PassManagerStagePlugin):
    """Translation stage plugin for the :mod:`qiskit.transpiler`.

    Register a :class:`WrapRxxAngles` pass after the preset pass irrespective of the optimization
    level. The pass enables the optimization stage to optimize the RXX gates with wrapped
    angles.

    If the optimization level is 0, an extra pass to decompose the wrapped RXX gates is
    added, as in this case no decomposition is being done by the optimization stage.

    Note: This plugin was originally created for Qiskit 1. Qiskit 2 introduces a transpiler pass
    :class:`WrapAngles <qiskit.transpiler.passes.WrapAngles>` for
    wrapping angles and it may be possible to find a better solution based on it.
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
            unitary_synthesis_method=pass_manager_config.unitary_synthesis_method,
            unitary_synthesis_plugin_config=pass_manager_config.unitary_synthesis_plugin_config,
            hls_config=pass_manager_config.hls_config,
        )

        translation_pm.append(WrapRxxAngles())
        if optimization_level is None or optimization_level == 0:
            translation_pm.append(Decompose([f"{WrapRxxAngles.SUBSTITUTE_GATE_NAME}*"]))

        return translation_pm


class AQTSchedulingPlugin(PassManagerStagePlugin):
    """Scheduling stage plugin for the :mod:`qiskit.transpiler`.

    Register the following passes to conclude transpilation, irrespective of the optimization level:
    1. :class:`WrapRxxAngles` pass to wrap Rxx angles to [0, π/2].
    2. Pass for the wrapped RXX gates decomposition.
    3. Single-qubit gates decomposition. It uses a RR decomposition, which emits code that requires
    two pulses per single-qubit gates run. Since Z gates are virtual, a ZXZ decomposition is
    better, because it only requires a single pulse.
    4. :class:`RewriteRxAsR` pass to rewrite RX → R, also wrapping the angles to match the API
    constraints.
    5. Remove redundant final measurements and raise error for mid-circuit measurements.

    Note: This plugin was originally created for Qiskit 1. Qiskit 2 introduces a transpiler pass
    :class:`WrapAngles <qiskit.transpiler.passes.WrapAngles>` for
    wrapping angles and it may be possible to find a better solution based on it.
    """

    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,  # noqa: ARG002
        optimization_level: Optional[int] = None,  # noqa: ARG002
    ) -> PassManager:
        """Pass manager for the scheduling phase."""
        passes: list[Task] = [
            WrapRxxAngles(),
            Decompose([f"{WrapRxxAngles.SUBSTITUTE_GATE_NAME}*"]),
            Optimize1qGatesDecomposition(basis=["rx", "rz"]),
            RewriteRxAsR(),
            EnsureSingleFinalMeasurement(),
        ]
        return PassManager(passes)
