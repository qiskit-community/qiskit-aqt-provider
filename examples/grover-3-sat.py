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

"""3-SAT solving example using the Grover algorithm.

This is a modified version of the corresponding
[Qiskit tutorial](https://qiskit.org/documentation/tutorials/algorithms/07_grover_examples.html).
"""


import tempfile
import textwrap
from typing import Final, Set, Tuple

from qiskit.algorithms import AmplificationProblem, Grover
from qiskit.circuit.library.phase_oracle import PhaseOracle

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives import AQTSampler


class ThreeSatProblem:
    """A 3-SAT problem, defined as DIMACS-CNF."""

    def __init__(self, dimacs_cnf: str, *, num_solutions: int):
        with tempfile.NamedTemporaryFile(mode="w+t", encoding="ascii") as fp:
            fp.write(dimacs_cnf)
            fp.flush()

            self.func = tweedledum.BoolFunction.from_dimacs_file(fp.name)
            self.oracle = PhaseOracle.from_dimacs_file(fp.name)
            self.num_solutions = num_solutions

    def is_solution(self, bits: str) -> bool:
        """Whether the given bitstring is a solution to the problem."""
        args = [tweedledum.BitVec(bit) for bit in reversed(bits)]
        return bool(self.func.simulate(*args))


def format_bitstring(bits: str) -> Tuple[bool, ...]:
    """Format a bitstring as tuple of boolean values.

    Warning: this reverses the bit order.
    In `bits`, the order is MSB-first. In the return value,
    the order is LSB-first.

    >>> format_bitstring("110")
    (False, True, True)

    >>> format_bitstring("001")
    (True, False, False)
    """
    return tuple(bool(int(bit)) for bit in reversed(bits))


if __name__ == "__main__":
    import tweedledum

    # Problem definition
    sat_problem = ThreeSatProblem(
        textwrap.dedent("""
            c example DIMACS-CNF 3-SAT
            p cnf 3 5
            -1 -2 -3 0
            1 -2 3 0
            1 2 -3 0
            1 -2 -3 0
            -1 2 3 0
            """),
        num_solutions=3,
    )

    # Select the sampling engine
    backend = AQTProvider("token").get_backend("offline_simulator_no_noise")
    sampler = AQTSampler(backend)

    # Map the problem to a Grover search
    problem = AmplificationProblem(sat_problem.oracle, is_good_state=sat_problem.is_solution)
    grover = Grover(
        iterations=Grover.optimal_num_iterations(sat_problem.num_solutions, 3), sampler=sampler
    )

    # Run the Grover search until all solutions are found
    MAX_ITERATIONS: Final = 100
    solutions: Set[str] = set()
    for _ in range(MAX_ITERATIONS):
        solutions.add(grover.amplify(problem).assignment)
        if len(solutions) == sat_problem.num_solutions:
            break
    else:  # pragma: no cover
        raise RuntimeError(f"Didn't find all solutions in {MAX_ITERATIONS} iterations.")

    for solution in solutions:
        print(format_bitstring(solution))
