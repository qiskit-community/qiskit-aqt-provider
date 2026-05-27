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

"""Basic example with the Qiskit AQT provider. Creates a 4-qubit GHZ state."""

import qiskit
from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider

if __name__ == "__main__":
    # Use the provider in a context manager to ensure proper cleanup of resources.
    with AQTProvider() as provider:
        backend = provider.offline.ideal()  # Get the ideal offline simulator resource.

        # Define a quantum circuit that produces a 4-qubit GHZ state.
        qc = QuantumCircuit(4)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(0, 2)
        qc.cx(0, 3)
        qc.measure_all()

        # Transpile for the target backend.
        qc = qiskit.transpile(qc, backend)

        # Execute on the target backend.
        result = backend.run(qc, shots=200).result()

        if result.success:
            print(result.get_counts())
        else:  # pragma: no cover
            print(result.to_dict()["error"])
