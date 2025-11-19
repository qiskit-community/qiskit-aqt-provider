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


from aqt_connector.models.arnica.jobs import JobType
from aqt_connector.models.arnica.request_bodies.jobs import QuantumCircuits as AQTQuantumCircuits
from aqt_connector.models.arnica.request_bodies.jobs import SubmitJobRequest
from aqt_connector.models.circuits import Circuit
from aqt_connector.models.circuits import QuantumCircuit as AQTQuantumCircuit
from aqt_connector.models.operations import (
    GateR,
    GateRXX,
    GateRZ,
    Measure,
    OperationModel,
)
from numpy import pi
from qiskit import QuantumCircuit
from typing_extensions import assert_never


def qiskit_to_aqt_circuit(circuit: QuantumCircuit) -> Circuit:
    """Convert a Qiskit `QuantumCircuit` into a payload for AQT's quantum_circuit job type.

    Args:
        circuit: Qiskit circuit to convert.

    Returns:
        AQT API circuit payload.
    """
    ops: list[OperationModel] = []
    num_measurements = 0

    for instruction in circuit.data:
        if instruction.operation.name != "measure" and num_measurements > 0:
            raise ValueError(
                "Measurement operations can only be located at the end of the circuit."
            )

        if instruction.operation.name == "rz":
            (phi,) = instruction.operation.params
            (qubit,) = instruction.qubits
            ops.append(
                OperationModel(
                    root=GateRZ(
                        phi=float(phi) / pi,
                        qubit=circuit.find_bit(qubit).index,
                    )
                )
            )
        elif instruction.operation.name == "r":
            theta, phi = instruction.operation.params
            (qubit,) = instruction.qubits
            ops.append(
                OperationModel(
                    root=GateR(
                        phi=float(phi) / pi,
                        theta=float(theta) / pi,
                        qubit=circuit.find_bit(qubit).index,
                    )
                )
            )
        elif instruction.operation.name == "rxx":
            (theta,) = instruction.operation.params
            q0, q1 = instruction.qubits
            ops.append(
                OperationModel(
                    root=GateRXX(
                        theta=float(theta) / pi,
                        qubits=[circuit.find_bit(q0).index, circuit.find_bit(q1).index],
                    )
                )
            )
        elif instruction.operation.name == "measure":
            num_measurements += 1
        elif instruction.operation.name == "barrier":
            continue
        else:
            raise ValueError(
                f"Operation '{instruction.operation.name}' not in basis gate set: {{rz, r, rxx}}"
            )

    if not num_measurements:
        raise ValueError("Circuit must have at least one measurement operation.")

    ops.append(OperationModel(root=Measure()))
    return Circuit(root=ops)


def aqt_to_qiskit_circuit(circuit: Circuit, number_of_qubits: int) -> QuantumCircuit:
    """Convert an AQT API quantum circuit payload to an equivalent Qiskit representation.

    Args:
        circuit: payload to convert
        number_of_qubits: size of the quantum register to use for the converted circuit.

    Returns:
        A :class:`QuantumCircuit <qiskit.circuit.quantumcircuit.QuantumCircuit>` equivalent
        to the passed circuit payload.
    """
    qiskit_circuit = QuantumCircuit(number_of_qubits)

    for operation in circuit.root:
        if isinstance(operation.root, GateRZ):
            qiskit_circuit.rz(operation.root.phi * pi, operation.root.qubit)
        elif isinstance(operation.root, GateR):
            qiskit_circuit.r(
                operation.root.theta * pi,
                operation.root.phi * pi,
                operation.root.qubit,
            )
        elif isinstance(operation.root, GateRXX):
            qiskit_circuit.rxx(operation.root.theta * pi, *operation.root.qubits)
        elif isinstance(operation.root, Measure):
            qiskit_circuit.measure_all()
        else:
            assert_never(operation.root)  # pragma: no cover

    return qiskit_circuit


def circuits_to_aqt_job(circuits: list[QuantumCircuit], shots: int) -> SubmitJobRequest:
    """Convert a list of circuits to the corresponding AQT API job request payload.

    Args:
        circuits: circuits to execute
        shots: number of repetitions per circuit.

    Returns:
        JobSubmission: AQT API payload for submitting the quantum circuits job.
    """
    return SubmitJobRequest(
        job_type=JobType.QUANTUM_CIRCUIT,
        label="qiskit",
        payload=AQTQuantumCircuits(
            circuits=[
                AQTQuantumCircuit(
                    repetitions=shots,
                    quantum_circuit=qiskit_to_aqt_circuit(circuit),
                    number_of_qubits=circuit.num_qubits,
                )
                for circuit in circuits
            ]
        ),
    )
