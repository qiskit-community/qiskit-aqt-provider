# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test helpers for quantum circuits."""

from qiskit import QuantumCircuit


def assert_circuits_equal(result: QuantumCircuit, expected: QuantumCircuit) -> None:
    """Assert result == expected, pretty-printing the circuits if they don't match."""
    msg = f"\nexpected:\n{expected}\nresult:\n{result}"
    assert result == expected, msg
