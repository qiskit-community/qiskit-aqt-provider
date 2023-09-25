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

from typing import List

from numpy import pi
from qiskit import QuantumCircuit

from qiskit_aqt_provider import api_models


def _qiskit_to_aqt_circuit(circuit: QuantumCircuit) -> api_models.Circuit:
    """Convert a Qiskit `QuantumCircuit` into a payload for AQT's quantum_circuit job type.

    Args:
        circuit: Qiskit circuit to convert.

    Returns:
        AQT API circuit payload.
    """
    count = 0
    qubit_map = {}
    for bit in circuit.qubits:
        qubit_map[bit] = count
        count += 1
    ops: List[api_models.OperationModel] = []

    num_measurements = 0

    for instruction in circuit.data:
        inst = instruction[0]
        qubits = [qubit_map[bit] for bit in instruction[1]]

        if inst.name != "measure" and num_measurements > 0:
            raise ValueError(
                "Measurement operations can only be located at the end of the circuit."
            )

        if inst.name == "rz":
            ops.append(
                api_models.Operation.rz(
                    phi=float(inst.params[0]) / pi,
                    qubit=qubits[0],
                )
            )
        elif inst.name == "r":
            ops.append(
                api_models.Operation.r(
                    phi=float(inst.params[1]) / pi,
                    theta=float(inst.params[0]) / pi,
                    qubit=qubits[0],
                )
            )
        elif inst.name == "rxx":
            ops.append(
                api_models.Operation.rxx(
                    theta=float(inst.params[0]) / pi,
                    qubits=qubits[:2],
                )
            )
        elif inst.name == "measure":
            num_measurements += 1
        elif inst.name == "barrier":
            continue
        else:
            raise ValueError(f"Operation '{inst.name}' not in basis gate set: {{rz, r, rxx}}")

    if not num_measurements:
        raise ValueError("Circuit must have at least one measurement operation.")

    ops.append(api_models.Operation.measure())
    return api_models.Circuit(__root__=ops)


def circuits_to_aqt_job(circuits: List[QuantumCircuit], shots: int) -> api_models.JobSubmission:
    """Convert a list of circuits to the corresponding AQT API job request payload.

    Args:
        circuits: circuits to execute
        shots: number of repetitions per circuit.

    Returns:
        JobSubmission: AQT API payload for submitting the quantum circuits job.
    """
    return api_models.JobSubmission(
        job_type="quantum_circuit",
        label="qiskit",
        payload=api_models.QuantumCircuits(
            circuits=[
                api_models.QuantumCircuit(
                    repetitions=shots,
                    quantum_circuit=_qiskit_to_aqt_circuit(circuit),
                    number_of_qubits=circuit.num_qubits,
                )
                for circuit in circuits
            ]
        ),
    )
