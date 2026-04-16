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

from math import pi

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTSampler

# Define a circuit
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

# Select an execution backend
backend = AQTProvider().get_backend("offline_simulator_no_noise")

# Instantiate a sampler on the execution backend
sampler = AQTSampler(backend=backend, auto_transpilation=False)

# Transpile the circuit for the execution backend
pm = generate_preset_pass_manager(backend=backend, optimization_level=3)
transpiled_circuit = pm.run(circuit)

# Sample the circuit on the execution backend
result = sampler.run([transpiled_circuit]).result()[0]

print(f">>> Results: {result.data.meas.get_bitstrings()}")
print(f">>> Result counts: {result.data.meas.get_counts()}")


# define a circuit with unbound parameters
theta_param = Parameter("θ")
qc = QuantumCircuit(2)
qc.rx(pi / 3, 0)
qc.rxx(theta_param, 0, 1)
qc.measure_all()

# sample the circuit, passing parameter assignments and let the sampler handle the transpilation
sampler = AQTSampler(backend=backend, optimization_level=0)
result = sampler.run([(qc, pi)], shots=33).result()[0]  # pyright: ignore[reportArgumentType]

print(f">>> Results: {result.data.meas.get_bitstrings()}")
print(f">>> Result counts: {result.data.meas.get_counts()}")
