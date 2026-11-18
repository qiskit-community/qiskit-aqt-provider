# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import pytest
from qiskit import QuantumCircuit
from qiskit.result import Result

from qiskit_aqt_provider._transformers import partial_qiskit_result_dict


@pytest.mark.parametrize(
    ("samples", "expected_memory"),
    [
        ([[0, 0], [1, 0], [0, 1], [1, 1]], ["0x0", "0x1", "0x2", "0x3"]),
        ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [1, 0, 1, 1]], ["0x0", "0x1", "0x8", "0xd"]),
        ([[0] * 9, [1] * 9, [0] * 8 + [1]], ["0x0", "0x1ff", "0x100"]),
    ],
)
def test_result_raw_memory_encoding(
    samples: list[list[int]],
    expected_memory: list[str],
) -> None:
    """Raw memory should be encoded as hexadecimal."""
    circuit = QuantumCircuit(len(samples[0]))
    circuit.measure_all()

    result = Result.from_dict(
        {
            "backend_name": "test",
            "backend_version": "1",
            "job_id": "test",
            "success": True,
            "results": [partial_qiskit_result_dict(samples, circuit, shots=len(samples), memory=True)],
        }
    )

    assert result.data()["memory"] == expected_memory


@pytest.mark.parametrize(
    ("samples", "expected_memory"),
    [
        ([[0, 0], [1, 0], [0, 1], [1, 1]], ["00", "01", "10", "11"]),
        ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [1, 0, 1, 1]], ["0000", "0001", "1000", "1101"]),
        ([[0] * 9, [1] * 9, [0] * 8 + [1]], ["000000000", "111111111", "100000000"]),
    ],
)
def test_result_public_memory_encoding(
    samples: list[list[int]],
    expected_memory: list[str],
) -> None:
    """Public memory should be encoded as binary."""
    circuit = QuantumCircuit(len(samples[0]))
    circuit.measure_all()

    result = Result.from_dict(
        {
            "backend_name": "test",
            "backend_version": "1",
            "job_id": "test",
            "success": True,
            "results": [partial_qiskit_result_dict(samples, circuit, shots=len(samples), memory=True)],
        }
    )

    assert result.get_memory() == expected_memory
