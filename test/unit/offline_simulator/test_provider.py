from qiskit_aqt_provider._offline_sim.provider import OfflineSimulatorProvider


def test_noisy_returns_simulator_with_noise_model() -> None:
    """The noisy method should return an offline simulator resource with the expected noise model."""
    provider = OfflineSimulatorProvider()

    resource = provider.noisy()

    assert resource.name == "offline_simulator_noise"
    assert resource.num_qubits == 20
    assert resource.simulator.options.noise_model is not None
    assert set(resource.simulator.options.noise_model.basis_gates) == {"r", "rz", "rxx"}
    assert set(resource.simulator.options.noise_model.noise_instructions) == {"r", "rxx"}


def test_ideal_returns_simulator_without_noise_model() -> None:
    """The ideal method should return an offline simulator resource without a noise model."""
    provider = OfflineSimulatorProvider()

    resource = provider.ideal()

    assert resource.name == "offline_simulator_no_noise"
    assert resource.num_qubits == 20
    assert resource.simulator.options.noise_model is None
