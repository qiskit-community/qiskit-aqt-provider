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

"""Quickstart example on transpiling and executing circuits."""

import qiskit
from qiskit.circuit.library import QuantumVolume

from qiskit_aqt_provider import AQTProvider

# Define a circuit
circuit = QuantumVolume(5)
circuit.measure_all()

# Select an execution backend
provider = AQTProvider("ACCESS_TOKEN")
backend = provider.get_backend("offline_simulator_no_noise")

# Transpile the circuit to target the selected AQT backend
transpiled_circuit = qiskit.transpile(circuit, backend, optimization_level=2)
print(transpiled_circuit)

# Execute the circuit on the selected AQT backend
result = backend.run(transpiled_circuit, shots=50).result()

if result.success:
    print(result.get_counts())
else:  # pragma: no cover
    raise RuntimeError
