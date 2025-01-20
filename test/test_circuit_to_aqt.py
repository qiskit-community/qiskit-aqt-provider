# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from math import pi

import pytest
import qiskit
from pydantic import ValidationError
from qiskit import QuantumCircuit

from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.aqt_resource import AQTResource
from qiskit_aqt_provider.circuit_to_aqt import (
    aqt_to_qiskit_circuit,
    circuits_to_aqt_job,
    qiskit_to_aqt_circuit,
)
from qiskit_aqt_provider.test.circuits import (
    assert_circuits_equal_ignore_global_phase,
    assert_circuits_equivalent,
    empty_circuit,
    qft_circuit,
    random_circuit,
)


def test_no_circuit() -> None:
    """Cannot convert an empty list of circuits to an AQT job request."""
    with pytest.raises(ValidationError):
        circuits_to_aqt_job([], shots=1)


def test_empty_circuit() -> None:
    """Circuits need at least one measurement operation."""
    qc = QuantumCircuit(1)
    with pytest.raises(ValueError):
        circuits_to_aqt_job([qc], shots=1)


def test_just_measure_circuit() -> None:
    """Circuits with only measurement operations are valid."""
    shots = 100

    qc = QuantumCircuit(1)
    qc.measure_all()

    expected = api_models.SubmitJobRequest(
        job_type="quantum_circuit",
        label="qiskit",
        payload=api_models.QuantumCircuits(
            circuits=[
                api_models.QuantumCircuit(
                    repetitions=shots,
                    number_of_qubits=1,
                    quantum_circuit=api_models.Circuit(root=[api_models.Operation.measure()]),
                ),
            ]
        ),
    )

    result = circuits_to_aqt_job([qc], shots=shots)

    assert result == expected


def test_valid_circuit() -> None:
    """A valid circuit with all supported basis gates."""
    qc = QuantumCircuit(2)
    qc.r(pi / 2, 0, 0)
    qc.rz(pi / 5, 1)
    qc.rxx(pi / 2, 0, 1)
    qc.measure_all()

    result = circuits_to_aqt_job([qc], shots=1)

    expected = api_models.SubmitJobRequest(
        job_type="quantum_circuit",
        label="qiskit",
        payload=api_models.QuantumCircuits(
            circuits=[
                api_models.QuantumCircuit(
                    number_of_qubits=2,
                    repetitions=1,
                    quantum_circuit=api_models.Circuit(
                        root=[
                            api_models.Operation.r(theta=0.5, phi=0.0, qubit=0),
                            api_models.Operation.rz(phi=0.2, qubit=1),
                            api_models.Operation.rxx(theta=0.5, qubits=[0, 1]),
                            api_models.Operation.measure(),
                        ]
                    ),
                ),
            ]
        ),
    )

    assert result == expected


def test_invalid_gates_in_circuit() -> None:
    """Circuits must already be in the target basis when they are converted
    to the AQT wire format.
    """
    qc = QuantumCircuit(1)
    qc.h(0)  # not an AQT-resource basis gate
    qc.measure_all()

    with pytest.raises(ValueError, match="not in basis gate set"):
        circuits_to_aqt_job([qc], shots=1)


def test_invalid_measurements() -> None:
    """Measurement operations can only be located at the end of the circuit."""
    qc_invalid = QuantumCircuit(2, 2)
    qc_invalid.r(pi / 2, 0.0, 0)
    qc_invalid.measure([0], [0])
    qc_invalid.r(pi / 2, 0.0, 1)
    qc_invalid.measure([1], [1])

    with pytest.raises(ValueError, match="at the end of the circuit"):
        circuits_to_aqt_job([qc_invalid], shots=1)

    # same circuit as above, but with the measurements at the end is valid
    qc = QuantumCircuit(2, 2)
    qc.r(pi / 2, 0.0, 0)
    qc.r(pi / 2, 0.0, 1)
    qc.measure([0], [0])
    qc.measure([1], [1])

    result = circuits_to_aqt_job([qc], shots=1)
    expected = api_models.SubmitJobRequest(
        job_type="quantum_circuit",
        label="qiskit",
        payload=api_models.QuantumCircuits(
            circuits=[
                api_models.QuantumCircuit(
                    number_of_qubits=2,
                    repetitions=1,
                    quantum_circuit=api_models.Circuit(
                        root=[
                            api_models.Operation.r(theta=0.5, phi=0.0, qubit=0),
                            api_models.Operation.r(theta=0.5, phi=0.0, qubit=1),
                            api_models.Operation.measure(),
                        ]
                    ),
                ),
            ]
        ),
    )

    assert result == expected


def test_convert_multiple_circuits() -> None:
    """Convert multiple circuits. Check that the order is conserved."""
    qc0 = QuantumCircuit(2)
    qc0.r(pi / 2, 0.0, 0)
    qc0.rxx(pi / 2, 0, 1)
    qc0.measure_all()

    qc1 = QuantumCircuit(1)
    qc1.r(pi / 4, 0.0, 0)
    qc1.measure_all()

    result = circuits_to_aqt_job([qc0, qc1], shots=1)

    expected = api_models.SubmitJobRequest(
        job_type="quantum_circuit",
        label="qiskit",
        payload=api_models.QuantumCircuits(
            circuits=[
                api_models.QuantumCircuit(
                    number_of_qubits=2,
                    repetitions=1,
                    quantum_circuit=api_models.Circuit(
                        root=[
                            api_models.Operation.r(theta=0.5, phi=0.0, qubit=0),
                            api_models.Operation.rxx(theta=0.5, qubits=[0, 1]),
                            api_models.Operation.measure(),
                        ]
                    ),
                ),
                api_models.QuantumCircuit(
                    number_of_qubits=1,
                    repetitions=1,
                    quantum_circuit=api_models.Circuit(
                        root=[
                            api_models.Operation.r(theta=0.25, phi=0.0, qubit=0),
                            api_models.Operation.measure(),
                        ]
                    ),
                ),
            ],
        ),
    )

    assert result == expected


@pytest.mark.parametrize(
    "circuit",
    [
        pytest.param(empty_circuit(2, with_final_measurement=False), id="empty-2"),
        pytest.param(random_circuit(2, with_final_measurement=False), id="random-2"),
        pytest.param(random_circuit(3, with_final_measurement=False), id="random-3"),
        pytest.param(random_circuit(5, with_final_measurement=False), id="random-5"),
        pytest.param(qft_circuit(5), id="qft-5"),
    ],
)
def test_convert_circuit_round_trip(
    circuit: QuantumCircuit, offline_simulator_no_noise: AQTResource
) -> None:
    """Check that transpiled qiskit circuits can be round-tripped through the API format."""
    trans_qc = qiskit.transpile(circuit, offline_simulator_no_noise)
    # There's no measurement in the circuit, so unitary operator equality
    # can be used to check the transpilation result.
    assert_circuits_equivalent(trans_qc, circuit)

    # Add the measurement operation to allow conversion to the AQT API format.
    trans_qc.measure_all()

    aqt_circuit = qiskit_to_aqt_circuit(trans_qc)
    trans_qc_back = aqt_to_qiskit_circuit(aqt_circuit, trans_qc.num_qubits)

    # transpiled circuits can be exactly reconstructed, up to the global
    # phase which is irrelevant for execution
    assert_circuits_equal_ignore_global_phase(trans_qc_back, trans_qc)
