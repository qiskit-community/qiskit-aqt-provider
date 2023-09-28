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

# mypy: disable-error-code="no-untyped-def"

"""Quickstart example on using the Estimator primitive.

This examples uses a variational quantum eigensolver (VQE) to find
the ground state energy of a Hamiltonian.
"""

from qiskit.circuit.library import TwoLocal
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTEstimator

# Select an execution backend
provider = AQTProvider("ACCESS_TOKEN")
backend = provider.get_backend("offline_simulator_no_noise")

# Instantiate an estimator on the execution backend
estimator = AQTEstimator(backend)

# Specify the problem Hamiltonian
hamiltonian = SparsePauliOp.from_list(
    [
        ("II", -1.052373245772859),
        ("IZ", 0.39793742484318045),
        ("ZI", -0.39793742484318045),
        ("ZZ", -0.01128010425623538),
        ("XX", 0.18093119978423156),
    ]
)

# Define the VQE Ansatz, initial point, and cost function
ansatz = TwoLocal(num_qubits=2, rotation_blocks="ry", entanglement_blocks="cz")
initial_point = initial_point = [0] * 8


def cost_function(params, ansatz, hamiltonian, estimator):
    """Cost function for the VQE.

    Return the estimated expectation value of the Hamiltonian
    on the state prepared by the Ansatz circuit.
    """
    return estimator.run(ansatz, hamiltonian, parameter_values=params).result().values[0]


# Run the VQE using the SciPy minimizer routine
result = minimize(
    cost_function, initial_point, args=(ansatz, hamiltonian, estimator), method="cobyla"
)

# Print the found minimum eigenvalue
print(result.fun)
