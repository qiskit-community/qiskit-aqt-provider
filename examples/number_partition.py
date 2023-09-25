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

"""Simple number partition problem solving.

This example shows how to solve problems covered by the application
domains in the qiskit_optimization package.

Number partition: given a set of positive integers, determine whether
it can be split into two non-overlapping sets that have the same sum.
"""

from dataclasses import dataclass
from typing import Final, List, Set, Union

from qiskit.algorithms.minimum_eigensolvers import QAOA
from qiskit.algorithms.optimizers import COBYLA
from qiskit.utils import algorithm_globals
from qiskit_optimization.algorithms import MinimumEigenOptimizer, OptimizationResultStatus
from qiskit_optimization.applications import NumberPartition

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTSampler

RANDOM_SEED: Final = 0


@dataclass(frozen=True)
class Success:
    # type would be better as tuple[set[int], set[int]] but
    # NumberPartition.interpret returns list[list[int]].
    partition: List[List[int]]

    def verify(self) -> bool:
        a, b = self.partition
        return sum(a) == sum(b)


class Infeasible:
    pass


def solve_partition_problem(num_set: Set[int]) -> Union[Success, Infeasible]:
    """Solve a partition problem.

    Args:
        num_set: set of positive integers to partition into two distinct subsets
        with the same sum.

    Returns:
        Success: solutions to the problem exist and are returned
        Infeasible: the given set cannot be partitioned.
    """
    problem = NumberPartition(list(num_set))
    qp = problem.to_quadratic_program()

    meo = MinimumEigenOptimizer(
        min_eigen_solver=QAOA(sampler=AQTSampler(backend), optimizer=COBYLA())
    )
    result = meo.solve(qp)

    if result.status is OptimizationResultStatus.SUCCESS:
        return Success(partition=problem.interpret(result))

    if result.status is OptimizationResultStatus.INFEASIBLE:
        return Infeasible()

    raise RuntimeError("Unexpected optimizer status")  # pragma: no cover


if __name__ == "__main__":
    backend = AQTProvider("token").get_backend("offline_simulator_no_noise")

    # fix the random seeds such that the example is reproducible
    algorithm_globals.random_seed = RANDOM_SEED
    backend.simulator.options.seed_simulator = RANDOM_SEED

    num_set = {1, 3, 4}
    result = solve_partition_problem(num_set)
    assert isinstance(result, Success)  # noqa: S101
    assert result.verify()  # noqa: S101
    print(f"Partition for {num_set}:", result.partition)

    num_set = {1, 2}
    result = solve_partition_problem(num_set)
    assert isinstance(result, Infeasible)  # noqa: S101
    print(f"No partition possible for {num_set}.")
