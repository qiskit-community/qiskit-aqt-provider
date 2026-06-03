from collections.abc import Sequence
from dataclasses import dataclass
from typing import Unpack

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import RGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target
from qiskit_aer import AerSimulator

from qiskit_aqt_provider._offline_sim.job import OfflineSimulatorJob
from qiskit_aqt_provider.options import ResourceRunOptions
from qiskit_aqt_provider.transpiler_plugin import TranspilerMixin


@dataclass
class OfflineSimulatorResourceConfig:
    name: str
    number_of_ions: int
    simulator: AerSimulator


class OfflineSimulatorResource(BackendV2, TranspilerMixin):
    """A resource for offline simulation."""

    MAX_SHOTS = 2000

    def __init__(self, config: OfflineSimulatorResourceConfig) -> None:
        """Initialize the resource with the given configuration."""
        self._resource_id = config.name
        super().__init__(name=config.name)
        self._update_target(config.number_of_ions)
        self.simulator = config.simulator

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return self._resource_id

    @property
    def target(self) -> Target:
        """The resource's target."""
        return self._target

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return 50

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
    ) -> OfflineSimulatorJob:
        """Run a quantum circuit or a sequence of quantum circuits on the offline simulator.

        Args:
            circuit (QuantumCircuit | Sequence[QuantumCircuit]): The quantum circuit(s) to run.
            shots (int | None): The number of shots to execute. If not provided, the default from the resource's options
                will be used.
            seed_simulator (int | None): The seed for the simulator's random number generator.
            memory (bool | None): Whether to return memory slots. Default is False.

        Returns:
            OfflineSimulatorJob: The job representing the simulation.
        """
        shots = kwargs.get("shots")
        if shots is None:
            shots = self._options.shots
        seed_simulator = kwargs.get("seed_simulator")
        if shots < 1 or shots > self.MAX_SHOTS:
            raise ValueError(f"Shots must be in the range [1, {self.MAX_SHOTS}].")
        aer_job = self.simulator.run(
            circuit, shots=shots, seed_simulator=seed_simulator, memory=kwargs.get("memory") or False
        )
        return OfflineSimulatorJob(aer_job)

    def _update_target(self, num_qubits: int) -> None:
        """Updates the target of this resource based on the given number of qubits."""
        theta = Parameter("θ")
        phi = Parameter("φ")
        lam = Parameter("λ")

        target = Target(num_qubits=num_qubits)
        target.add_instruction(RZGate(lam))
        target.add_instruction(RGate(theta, phi))
        target.add_instruction(RXXGate(theta))
        target.add_instruction(Measure())

        self._target = target
