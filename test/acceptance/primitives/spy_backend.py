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

from collections.abc import Sequence

from qiskit.circuit import QuantumCircuit
from qiskit.providers import BackendV2, JobV1, Options
from qiskit.transpiler import Target
from qiskit_aer import AerSimulator
from typing_extensions import Unpack

from qiskit_aqt_provider._offline_sim.resource import OfflineSimulatorResource, OfflineSimulatorResourceConfig
from qiskit_aqt_provider.options import ResourceRunOptions


class SpyBackend(BackendV2):
    """A backend that wraps an OfflineSimulatorResource and records calls to its run method."""

    def __init__(self) -> None:
        """Initialize the backend."""
        self._resource_id = "spy_backend"
        super().__init__(name=self._resource_id)
        self.simulator = AerSimulator(method="statevector")
        self._backend = OfflineSimulatorResource(
            OfflineSimulatorResourceConfig(
                name="spy_backend",
                number_of_ions=20,
                simulator=self.simulator,
            )
        )
        self._options = self._backend._options

        self.run_calls: list[tuple[QuantumCircuit | Sequence[QuantumCircuit], ResourceRunOptions]] = []
        self.run_responses: list[JobV1] = []

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return "spy_backend"

    @property
    def target(self) -> Target:
        """The resource's target."""
        return self._backend.target

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return self._backend.max_circuits

    @classmethod
    def _default_options(cls) -> Options:
        """Get the default options.

        Returns:
            Options: The default options for this resource.
        """
        return Options()

    def run(
        self,
        circuit: QuantumCircuit | Sequence[QuantumCircuit],
        **kwargs: Unpack[ResourceRunOptions],
    ) -> JobV1:
        """Run a quantum circuit or a sequence of quantum circuits on the backend, while recording the call."""
        self.run_calls.append((circuit, kwargs))
        job = self._backend.run(circuit, **kwargs)
        self.run_responses.append(job)
        return job
