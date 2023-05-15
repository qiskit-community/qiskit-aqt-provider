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

"""Trivial minimization example using a variational quantum eigensolver."""

from typing import Final

from qiskit.algorithms.minimum_eigensolvers import VQE
from qiskit.algorithms.optimizers import COBYLA
from qiskit.circuit.library import TwoLocal
from qiskit.quantum_info import SparsePauliOp
from qiskit.utils import algorithm_globals

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import OfflineSimulatorResource
from qiskit_aqt_provider.primitives.estimator import AQTEstimator

RANDOM_SEED: Final = 0

if __name__ == "__main__":
    backend = AQTProvider("token").get_backend("offline_simulator_no_noise")
    assert isinstance(backend, OfflineSimulatorResource)  # noqa: S101
    estimator = AQTEstimator(backend)

    # fix the random seeds such that the example is reproducible
    algorithm_globals.random_seed = RANDOM_SEED
    backend.simulator.options.seed_simulator = RANDOM_SEED

    # Hamiltonian: Ising model on two spin 1/2 without external field
    J = 1.2
    hamiltonian = SparsePauliOp.from_list([("XX", J)])

    # Find the ground-state energy with VQE
    ansatz = TwoLocal(num_qubits=2, rotation_blocks="ry", entanglement_blocks="rxx", reps=1)
    optimizer = COBYLA(maxiter=100, tol=0.01)
    vqe = VQE(estimator, ansatz, optimizer)
    result = vqe.compute_minimum_eigenvalue(operator=hamiltonian)
    assert result.eigenvalue is not None  # noqa: S101

    print(f"Optimizer run time: {result.optimizer_time:.2f} s")
    print("Cost function evaluations:", result.cost_function_evals)
    print("Deviation from expected ground-state energy:", abs(result.eigenvalue - (-J)))
