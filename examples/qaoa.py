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

"""Trivial minimization example using a quantum approximate optimization algorithm (QAOA).

This is the same example as in vqe.py, but uses QAOA instead of VQE as solver.
"""

from typing import Final

from qiskit.algorithms.minimum_eigensolvers import QAOA
from qiskit.algorithms.optimizers import COBYLA
from qiskit.quantum_info import SparsePauliOp
from qiskit.utils import algorithm_globals

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTSampler

RANDOM_SEED: Final = 0

if __name__ == "__main__":
    backend = AQTProvider("token").get_backend("offline_simulator_no_noise")
    sampler = AQTSampler(backend)

    # fix the random seeds such that the example is reproducible
    algorithm_globals.random_seed = RANDOM_SEED
    backend.simulator.options.seed_simulator = RANDOM_SEED

    # Hamiltonian: Ising model on two spin 1/2 without external field
    J = 1.23456789
    hamiltonian = SparsePauliOp.from_list([("ZZ", 3 * J)])

    # Find the ground-state energy with QAOA
    optimizer = COBYLA(maxiter=100, tol=0.01)
    qaoa = QAOA(sampler, optimizer)
    result = qaoa.compute_minimum_eigenvalue(operator=hamiltonian)
    assert result.eigenvalue is not None  # noqa: S101

    print(f"Optimizer run time: {result.optimizer_time:.2f} s")
    print("Cost function evaluations:", result.cost_function_evals)
    print("Deviation from expected ground-state energy:", abs(result.eigenvalue - (-3 * J)))
