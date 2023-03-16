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
from typing import List, Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RGate
from qiskit.circuit.quantumregister import Qubit
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import BasePass, TransformationPass
from qiskit.transpiler.passmanager import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin


class RewriteRxRyAsR(TransformationPass):
    """Rewrite all `RXGate` and `RYGate` instances as `RGate`. Wrap the rotation angle to [-π, π]."""

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        for node in dag.gate_nodes():
            if node.name in {"rx", "ry"}:
                (theta,) = node.op.params
                phi = math.pi / 2 if node.name == "ry" else 0.0
                new_theta = math.atan2(math.sin(float(theta)), math.cos(float(theta)))
                dag.substitute_node(node, RGate(new_theta, phi))
        return dag


class AQTSchedulingPlugin(PassManagerStagePlugin):
    def pass_manager(
        self, pass_manager_config: PassManagerConfig, optimization_level: Optional[int] = None
    ) -> PassManager:
        passes: List[BasePass] = [
            # The Qiskit Target declares RX/RZ as basis gates.
            # This allows decomposing any run of rotations into the ZXZ form, taking
            # advantage of the free Z rotations.
            # Since the API expects R/RZ as single-qubit operations,
            # we rewrite all RX/RY gates as R gates after optimizations have been performed.
            RewriteRxRyAsR(),
        ]

        return PassManager(passes)


def wrap_rxx_angle(theta: float, q0: Qubit, q1: Qubit) -> QuantumCircuit:
    """Circuit equivalent to RXX(theta, q0, q1) with the RXX angle in [-π/2, π/2]."""

    qr = {q0.register, q1.register}

    theta %= 2 * math.pi

    if abs(theta) <= math.pi / 2:
        qc = QuantumCircuit(*qr)
        qc.rxx(theta, q0, q1)
        return qc

    if abs(theta) < 3 * math.pi / 2:
        corrected_angle = theta - np.sign(theta) * math.pi
        qc = QuantumCircuit(*qr)
        qc.rx(math.pi, q0)
        qc.rx(math.pi, q1)
        qc.rxx(corrected_angle, q0, q1)
        return qc

    corrected_angle = theta - np.sign(theta) * 2 * math.pi
    qc = QuantumCircuit(*qr)
    qc.rxx(corrected_angle, q0, q1)
    return qc


class WrapRxxAngles(TransformationPass):
    """Wrap Rxx angles to [-π/2, π/2]."""

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        for node in dag.gate_nodes():
            if node.name == "rxx":
                (theta,) = node.op.params

                if abs(float(theta)) <= math.pi / 2:
                    continue

                q0, q1 = node.qargs
                qc = wrap_rxx_angle(float(theta), q0, q1)
                dag.substitute_node_with_dag(node, circuit_to_dag(qc))

        return dag


class AQTTranslationPlugin(PassManagerStagePlugin):
    def pass_manager(
        self, pass_manager_config: PassManagerConfig, optimization_level: Optional[int] = None
    ) -> PassManager:
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

        passes: List[BasePass] = [WrapRxxAngles()]

        return translation_pm + PassManager(passes)
