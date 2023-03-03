# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import json
from typing import Any, Dict, List

from numpy import pi
from qiskit import QuantumCircuit


def _experiment_to_seq(circuit):
    count = 0
    qubit_map = {}
    for bit in circuit.qubits:
        qubit_map[bit] = count
        count += 1
    ops = []
    meas = 0
    for instruction in circuit.data:
        inst = instruction[0]
        qubits = [qubit_map[bit] for bit in instruction[1]]
        if inst.name == "rx":
            name = "X"
        elif inst.name == "ry":
            name = "Y"
        elif inst.name == "rz":
            name = "Z"
        elif inst.name == "r":
            name = "R"
        elif inst.name == "rxx":
            name = "MS"
        elif inst.name == "ms":
            name = "MS"
            qubits = []
        elif inst.name == "measure":
            meas += 1
            continue
        elif inst.name == "barrier":
            continue
        else:
            raise ValueError(f"Operation '{inst.name}' outside of basis rx, ry, rxx")
        exponent = inst.params[0] / pi
        # hack: split X into X**0.5 . X**0.5
        if name == "X" and exponent == 1.0:
            ops.append((name, float(0.5), qubits))
            ops.append((name, float(0.5), qubits))
        else:
            # (op name, exponent, [qubit index])
            ops.append((name, float(exponent), qubits))
    if not meas:
        raise ValueError("Circuit must have at least one measurements.")
    return json.dumps(ops)


def _experiment_to_aqt_circuit(circuit: QuantumCircuit) -> List[Dict[str, Any]]:
    count = 0
    qubit_map = {}
    for bit in circuit.qubits:
        qubit_map[bit] = count
        count += 1
    ops = []
    meas = 0
    for instruction in circuit.data:
        inst = instruction[0]
        qubits = [qubit_map[bit] for bit in instruction[1]]
        if inst.name == "rz":
            ops.append(
                {"gate": "RZ", "phi": float(inst.params[0]) / pi, "qubit": qubits[0]}
            )
        elif inst.name == "r":
            ops.append(
                {
                    "gate": "R",
                    "phi": float(inst.params[1]) / pi,
                    "theta": float(inst.params[0]) / pi,
                    "qubit": qubits[0],
                }
            )
        elif inst.name == "rxx":
            ops.append(
                {
                    "gate": "XX",
                    "qubits": qubits[:2],
                }
            )
        elif inst.name == "measure":
            # FIXME: we only support measurements at the end
            meas += 1
            continue
        elif inst.name == "barrier":
            continue
        else:
            raise ValueError(f"Operation '{inst.name}' outside of basis rz, r, rxx")
    if not meas:
        raise ValueError("Circuit must have at least one measurements.")
    return ops


def circuit_to_aqt(circuits, access_token, shots=100):
    """Return a list of json payload strings for each experiment in a qobj

    The output json format of an experiment is defined as follows:
        [[op_string, gate_exponent, qubits]]

    which is a list of sequential quantum operations, each operation defined
    by:

    op_string: str that specifies the operation type, either "X","Y","MS"
    gate_exponent: float that specifies the gate_exponent of the operation
    qubits: list of qubits where the operation acts on.
    """
    out_json = []
    if isinstance(circuits, list):
        if len(circuits) > 1:
            raise ValueError("Lists of circuits are not supported.")
        circuits = circuits[0]
    seqs = _experiment_to_seq(circuits)
    out_dict = {
        "data": seqs,
        "access_token": access_token,
        "repetitions": shots,
        "no_qubits": circuits.num_qubits,
    }
    out_json.append(out_dict)
    return out_json


def circuit_to_aqt_new(circuit: QuantumCircuit, shots: int) -> Dict[str, Any]:
    """Convert a Qiskit `QuantumCircuit` into a JSON-serializable payload describing
    a circuit execution request on the AQT API.

    Parameters:
        circuit (QuantumCircuit): The quantum circuit to convert
        shots (int): Number of repetitions

    Returns:
        The corresponding circuit execution request payload.
    """
    seqs = _experiment_to_aqt_circuit(circuit)

    out_dict = {
        "job_type": "quantum_circuit",
        "label": "qiskit",
        "payload": {"repetitions": shots, "quantum_circuit": seqs},
    }
    return out_dict
