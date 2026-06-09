from collections import Counter, defaultdict
from typing import Any

import numpy as np
from aqt_connector.models.arnica.jobs import JobType
from aqt_connector.models.arnica.request_bodies.jobs import QuantumCircuits as AQTQuantumCircuits
from aqt_connector.models.arnica.request_bodies.jobs import SubmitJobRequest
from aqt_connector.models.circuits import Circuit
from aqt_connector.models.circuits import QuantumCircuit as AQTQuantumCircuit
from aqt_connector.models.operations import GateR, GateRXX, GateRZ, Measure, OperationModel
from numpy import pi
from qiskit import QuantumCircuit
from qiskit.providers.jobstatus import JobStatus
from qiskit.utils.lazy_tester import contextlib


def partial_qiskit_result_dict(
    samples: list[list[int]], circuit: QuantumCircuit, *, shots: int, memory: bool
) -> dict[str, Any]:
    """Build the Qiskit result dict for a single circuit evaluation.

    Args:
        samples: measurement outcome of the circuit evaluation.
        circuit: the evaluated circuit.
        shots: number of repetitions of the circuit evaluation.
        memory: whether to fill the classical memory dump field with the measurement results.

    Returns:
        Dict, suitable for Qiskit's `Result.from_dict` factory.
    """
    meas_map = _build_memory_mapping(circuit)

    data: dict[str, Any] = {"counts": _format_counts(samples, meas_map)}

    if memory:
        # build per-shot classical memory strings using the measurement mapping
        mem_slots = circuit.num_clbits
        memory_list: list[str] = []
        for states in samples:
            # initialize classical register (all 0)
            creg = ["0"] * mem_slots
            for src_index, dest_indices in meas_map.items():
                if src_index < len(states):
                    src_bit = str(states[src_index])
                    for dest_index in dest_indices:
                        # place measured bit into the classical register position(s)
                        if 0 <= dest_index < mem_slots:
                            creg[dest_index] = src_bit
            # Qiskit orders memory strings with bit 0 as least-significant (rightmost)
            memory_list.append("".join(reversed(creg)))
        data["memory"] = memory_list

    return {
        "shots": shots,
        "success": True,
        "status": JobStatus.DONE,
        "data": data,
        "header": {
            "memory_slots": circuit.num_clbits,
            "creg_sizes": [[reg.name, reg.size] for reg in circuit.cregs],
            "qreg_sizes": [[reg.name, reg.size] for reg in circuit.qregs],
            "name": circuit.name,
            "metadata": circuit.metadata or {},
        },
    }


def _build_memory_mapping(circuit: QuantumCircuit) -> dict[int, set[int]]:
    """Scan the circuit for measurement instructions and collect qubit to classical bits mappings.

    Qubits can be mapped to multiple classical bits, possibly in different classical registers.
    The returned map only maps qubits referenced in a `measure` operation in the passed circuit.
    Qubits not targeted by a `measure` operation will not appear in the returned result.

    Parameters:
        circuit: the `QuantumCircuit` to analyze.

    Returns:
        the translation map for all measurement operations in the circuit.

    Examples:
        >>> qc = QuantumCircuit(2)
        >>> qc.measure_all()
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        >>> qc = QuantumCircuit(2, 2)
        >>> _ = qc.measure([0, 1], [1, 0])
        >>> _build_memory_mapping(qc)
        {0: {1}, 1: {0}}

        >>> qc = QuantumCircuit(3, 2)
        >>> _ = qc.measure([0, 1], [0, 1])
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        >>> qc = QuantumCircuit(4, 6)
        >>> _ = qc.measure([0, 1, 2, 3], [2, 3, 4, 5])
        >>> _build_memory_mapping(qc)
        {0: {2}, 1: {3}, 2: {4}, 3: {5}}

        >>> qc = QuantumCircuit(3, 4)
        >>> qc.measure_all(add_bits=False)
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}, 2: {2}}

        >>> qc = QuantumCircuit(3, 3)
        >>> _ = qc.x(0)
        >>> _ = qc.measure([0], [2])
        >>> _ = qc.y(1)
        >>> _ = qc.measure([1], [1])
        >>> _ = qc.x(2)
        >>> _ = qc.measure([2], [0])
        >>> _build_memory_mapping(qc)
        {0: {2}, 1: {1}, 2: {0}}

        5 qubits in two registers:

        >>> from qiskit import QuantumRegister, ClassicalRegister
        >>> qr0 = QuantumRegister(2)
        >>> qr1 = QuantumRegister(3)
        >>> cr = ClassicalRegister(2)
        >>> qc = QuantumCircuit(qr0, qr1, cr)
        >>> _ = qc.measure(qr0, cr)
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        Multiple mapping of a qubit:

        >>> qc = QuantumCircuit(3, 3)
        >>> _ = qc.measure([0, 1], [0, 1])
        >>> _ = qc.measure([0], [2])
        >>> _build_memory_mapping(qc)
        {0: {0, 2}, 1: {1}}
    """
    qu2cl: defaultdict[int, set[int]] = defaultdict(set)

    for instruction in circuit.data:
        if instruction.operation.name == "measure":
            for qubit, clbit in zip(instruction.qubits, instruction.clbits):
                qu2cl[circuit.find_bit(qubit).index].add(circuit.find_bit(clbit).index)

    return dict(qu2cl)


def _shot_to_int(fluorescence_states: list[int], qubit_to_bit: dict[int, set[int]] | None = None) -> int:
    """Format the detected fluorescence states from a single shot as an integer.

    This follows the Qiskit ordering convention, where bit 0 in the classical register is mapped
    to bit 0 in the returned integer. The first classical register in the original circuit
    represents the least-significant bits in the integer representation.

    An optional translation map from the quantum to the classical register can be applied.
    If given, only the qubits registered in the translation map are present in the return value,
    at the index given by the translation map.

    Parameters:
        fluorescence_states: detected fluorescence states for this shot
        qubit_to_bit: optional translation map from quantum register to classical register positions

    Returns:
        integral representation of the shot result, with the translation map applied.

    Examples:
       Without a translation map, the natural mapping is used (n -> n):

        >>> _shot_to_int([1])
        1

        >>> _shot_to_int([0, 0, 1])
        4

        >>> _shot_to_int([0, 1, 1])
        6

        Swap qubits 1 and 2 in the classical register:

        >>> _shot_to_int([1, 0, 1], {0: {0}, 1: {2}, 2: {1}})
        3

        If the map is partial, only the mapped qubits are present in the output:

        >>> _shot_to_int([1, 0, 1], {1: {2}, 2: {1}})
        2

        One can translate into a classical register larger than the
        qubit register.

        Warning: the classical register is always initialized to 0.

        >>> _shot_to_int([1], {0: {1}})
        2

        >>> _shot_to_int([0, 1, 1], {0: {3}, 1: {4}, 2: {5}}) == (0b110 << 3)
        True

        or with a map larger than the qubit space:

        >>> _shot_to_int([1], {0: {0}, 1: {1}})
        1

        Consider the typical example of two quantum registers (the second one contains
        ancilla qubits) and one classical register:

        >>> from qiskit import QuantumRegister, ClassicalRegister
        >>> qr_meas = QuantumRegister(2)
        >>> qr_ancilla = QuantumRegister(3)
        >>> cr = ClassicalRegister(2)
        >>> qc = QuantumCircuit(qr_meas, qr_ancilla, cr)
        >>> _ = qc.measure(qr_meas, cr)
        >>> tr_map = _build_memory_mapping(qc)

        We assume that a single shot gave the result:

        >>> ancillas = [1, 1, 0]
        >>> meas = [1, 0]

        Then the corresponding output is 0b01 (measurement qubits mapped straight
        to the classical register of length 2):

        >>> _shot_to_int(meas + ancillas, tr_map) == 0b01
        True

        One can overwrite qr_meas[1] with qr_ancilla[0]:

        >>> _ = qc.measure(qr_ancilla[0], cr[1])
        >>> tr_map = _build_memory_mapping(qc)
        >>> _shot_to_int(meas + ancillas, tr_map) == 0b11
        True
    """
    tr_map = qubit_to_bit or {}

    if tr_map:
        # allocate a zero-initialized classical register
        # TODO: support pre-initialized classical registers
        clbits = max(max(d) for d in tr_map.values()) + 1
        creg = [0] * clbits

        for src_index, dest_indices in tr_map.items():
            # the translation map could map more than just the measured qubits
            with contextlib.suppress(IndexError):
                for dest_index in dest_indices:
                    creg[dest_index] = fluorescence_states[src_index]
    else:
        creg = fluorescence_states.copy()

    return int((np.left_shift(1, np.arange(len(creg))) * creg).sum())


def _format_counts(samples: list[list[int]], qubit_to_bit: dict[int, set[int]] | None = None) -> dict[str, int]:
    """Format all shots results from a circuit evaluation.

    The returned dictionary is compatible with Qiskit's `ExperimentResultData`
    `counts` field.

    Keys are hexadecimal string representations of the detected states, with the
    optional `QuantumRegister` to `ClassicalRegister` applied. Values are the occurrences
    of the keys.

    Parameters:
        samples: detected qubit fluorescence states for all shots
        qubit_to_bit: optional quantum to classical register translation map

    Returns:
        collected counts, for `ExperimentResultData`.

    Examples:
        >>> _format_counts([[1, 0, 0], [0, 1, 0], [1, 0, 0]])
        {'0x1': 2, '0x2': 1}

        >>> _format_counts([[1, 0, 0], [0, 1, 0], [1, 0, 0]], {0: {2}, 1: {1}, 2: {0}})
        {'0x4': 2, '0x2': 1}
    """
    return dict(Counter(hex(_shot_to_int(shot, qubit_to_bit)) for shot in samples))


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
            raise ValueError("Measurement operations can only be located at the end of the circuit.")

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
            raise ValueError(f"Operation '{instruction.operation.name}' not in basis gate set: {{rz, r, rxx}}")

    if not num_measurements:
        raise ValueError("Circuit must have at least one measurement operation.")

    ops.append(OperationModel(root=Measure()))
    return Circuit(root=ops)


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
