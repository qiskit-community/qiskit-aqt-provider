from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from qiskit_aqt_provider._offline_sim.resource import OfflineSimulatorResource, OfflineSimulatorResourceConfig


class OfflineSimulatorProvider:
    """A provider for offline simulators."""

    def noisy(self) -> OfflineSimulatorResource:
        """Returns a noisy offline simulator resource."""
        noise_model = NoiseModel(basis_gates=["r", "rz", "rxx"])
        noise_model.add_all_qubit_quantum_error(depolarizing_error(0.003, 1), ["r"])
        noise_model.add_all_qubit_quantum_error(depolarizing_error(0.01, 2), ["rxx"])

        return OfflineSimulatorResource(
            config=OfflineSimulatorResourceConfig(
                name="offline_simulator_noise",
                number_of_ions=20,
                simulator=AerSimulator(method="statevector", noise_model=noise_model),
            )
        )

    def ideal(self) -> OfflineSimulatorResource:
        """Returns an ideal offline simulator resource."""
        return OfflineSimulatorResource(
            config=OfflineSimulatorResourceConfig(
                name="offline_simulator_no_noise",
                number_of_ions=20,
                simulator=AerSimulator(method="statevector"),
            )
        )
