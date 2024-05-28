# (C) Copyright Alpine Quantum Technologies 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for the experimental QIR to AQT JSON API converter.

Note: no tests involve RXXGate because (as of 2024-05-28):
- qiskit_qir doesn't support RXXGate as native gate, thus emitting unsupported CNOT/H calls.
- pyqir has no builder for this gate.
- writing LLVM IR by hand is tedious and brittle.
"""

import textwrap
from collections import namedtuple
from math import pi

import pyqir
import pytest
from qiskit import QuantumCircuit
from qiskit_qir import to_qir_module

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.circuit_to_aqt import (
    aqt_to_qiskit_circuit,
    qiskit_to_aqt_circuit,
)
from qiskit_aqt_provider.qir_to_aqt import load_llvm_module, qir_to_aqt_circuit
from qiskit_aqt_provider.test.circuits import (
    assert_circuits_equivalent,
)


def test_empty_circuit() -> None:
    """Valid circuits contain at least one measurement operation."""
    qc = QuantumCircuit(2)
    mod, _ = to_qir_module(qc, record_output=False)

    with pytest.raises(ValueError, match=r"No measurement operations? found"):
        qir_to_aqt_circuit(mod)


def test_measure_only_circuit() -> None:
    """Circuit with only measurement operations are valid."""
    qc = QuantumCircuit(2)
    qc.measure_all()
    mod, _ = to_qir_module(qc, record_output=False)

    aqt_circ = qir_to_aqt_circuit(mod)
    assert aqt_circ == api_models.Circuit(root=[api_models.Operation.measure()])


def test_operate_after_measurement() -> None:
    """On a given qubit, operations after measurement are invalid."""
    qc = QuantumCircuit(1)
    qc.measure_all()
    qc.x(0)
    mod, _ = to_qir_module(qc, record_output=False)

    with pytest.raises(ValueError, match=r"Cannot operate on qubit=0"):
        qir_to_aqt_circuit(mod)


def test_unsupported_gates() -> None:
    """CX (CNOT) gates are not supported."""
    qc = QuantumCircuit(2)
    qc.cx(0, 1)
    qc.measure_all()

    mod, _ = to_qir_module(qc, record_output=False)

    with pytest.raises(ValueError, match=r"Unsupported function: (.*)__qis__cnot"):
        qir_to_aqt_circuit(mod)


def test_equivalent_on_single_qubit_basis_gates() -> None:
    """Example circuit with single-qubit native gates.

    Check that the AQT JSON payload is the same with the direct
    exporter and the QIR converter.
    """
    # The input circuit for both cases in not exactly the same
    # because:
    # - qiskit_qir.to_qir_module doesn't support RGate as native gate.
    # - the direct conversion needs native gate, so RXGate, RYGate, etc. are not supported.
    Arg = namedtuple("Arg", "angle,axis,qubit")  # noqa: PYI024

    args = [
        Arg(pi / 2, "x", 0),
        Arg(pi / 4, "x", 1),
        Arg(pi / 7, "y", 0),
        Arg(pi / 3, "z", 1),
    ]

    qc = QuantumCircuit(2)
    for arg in args:
        if arg.axis == "x":
            qc.rx(arg.angle, arg.qubit)
        elif arg.axis == "y":
            qc.ry(arg.angle, arg.qubit)
        elif arg.axis == "z":
            qc.rz(arg.angle, arg.qubit)
    qc.measure_all()

    mod, _ = to_qir_module(qc, record_output=False)
    from_qir = qir_to_aqt_circuit(mod)

    qc = QuantumCircuit(2)
    for arg in args:
        if arg.axis in ("x", "y"):
            phi = 0.0 if arg.axis == "x" else pi / 2
            qc.r(arg.angle, phi, arg.qubit)
        else:
            qc.rz(arg.angle, arg.qubit)
    qc.measure_all()

    direct = qiskit_to_aqt_circuit(qc)

    assert from_qir == direct


def test_unsupported_classical_control_flow() -> None:
    """Classical control flow is not supported."""
    qir = textwrap.dedent(r"""
        source_filename = "testcase"

        define void @entry() #0 {
        entry:
          call void @__quantum__rt__initialize(i8* null)
          br i1 1, label %then, label %else

        then:
          ret void

        else:
          ret void
        }

        declare void @__quantum__rt__initialize(i8*)

        attributes #0 = {"entry_point"}
    """)

    mod = load_llvm_module(qir)

    with pytest.raises(ValueError, match=r"Unsupported instruction(.*)br"):
        qir_to_aqt_circuit(mod)


def test_no_entry_point() -> None:
    """At least one entry point is required."""
    qir = textwrap.dedent(r"""
        source_filename = "testcase"

        define void @entry() {
        entry:
          call void @__quantum__rt__initialize(i8* null)
          ret void
        }

        declare void @__quantum__rt__initialize(i8*)
    """)

    mod = load_llvm_module(qir)

    with pytest.raises(ValueError, match="No entry point found"):
        qir_to_aqt_circuit(mod)


@pytest.mark.parametrize("from_bitcode", [True, False])
def test_load_from_bitcode_or_human_readable(from_bitcode: bool) -> None:
    """Load QIR input from bitcode or human-readable format."""
    mod = pyqir.SimpleModule("testcase", num_qubits=2, num_results=2)
    qis = pyqir.BasicQisBuilder(mod.builder)

    qis.x(mod.qubits[0])
    qis.y(mod.qubits[1])
    qis.mz(mod.qubits[0], mod.results[0])
    qis.mz(mod.qubits[1], mod.results[1])

    # equivalent circuit in native gates
    qc = QuantumCircuit(2)
    qc.r(pi, 0, 0)
    qc.r(pi, pi / 2, 1)
    qc.measure_all()

    loaded_mod = load_llvm_module(mod.bitcode() if from_bitcode else mod.ir())

    aqt_circ = qir_to_aqt_circuit(loaded_mod)
    ref_aqt_circ = qiskit_to_aqt_circuit(qc)

    assert aqt_circ == ref_aqt_circ


def test_demo_supported_single_qubit_qis_instructions() -> None:
    """Demo support single-qubit operations.

    Round-trip the test circuit from and to Qiskit, through
    QIR and the AQT JSON format. Check that the circuits are
    equivalent.
    """
    base_qc = QuantumCircuit(1)
    base_qc.rx(pi / 3, 0)
    base_qc.x(0)
    base_qc.ry(pi / 5, 0)
    base_qc.y(0)
    base_qc.rz(pi / 12, 0)
    base_qc.z(0)

    qc = base_qc.copy()
    qc.measure_all()

    mod, _ = to_qir_module(qc, record_output=False)
    aqt_circ = qir_to_aqt_circuit(mod)

    round_tripped = aqt_to_qiskit_circuit(aqt_circ, 1)
    round_tripped.remove_final_measurements()

    assert_circuits_equivalent(round_tripped, base_qc)
