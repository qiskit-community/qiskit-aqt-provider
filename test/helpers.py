# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


def assert_circuits_equivalent(circ1: QuantumCircuit, circ2: QuantumCircuit) -> None:
    """Helper function to assert that two quantum circuits are equivalent.

    This is done by comparing their unitary operators. Alternatively we could decompose both circuits
    and compare the resulting sequences of gates, but comparing unitaries is more straightforward for
    this test.
    """
    assert Operator(circ1).equiv(Operator(circ2))
