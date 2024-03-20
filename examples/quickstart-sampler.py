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

"""Quickstart example on using the Sampler primitive.

This example samples a 2-qubit Bell state.
"""

from qiskit import QuantumCircuit

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTSampler

# Define a circuit
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

# Select an execution backend
provider = AQTProvider("ACCESS_TOKEN")
backend = provider.get_backend("offline_simulator_no_noise")

# Instantiate a sampler on the execution backend
sampler = AQTSampler(backend)

# Set the transpiler's optimization level
sampler.set_transpile_options(optimization_level=3)

# Sample the circuit on the execution backend
result = sampler.run(circuit).result()

quasi_dist = result.quasi_dists[0]
print(quasi_dist)
