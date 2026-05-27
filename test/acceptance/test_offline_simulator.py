from qiskit_aqt_provider._offline_sim.resource import OfflineSimulatorResource
from test.acceptance import dsl


def test_acquire_simulator() -> None:
    """An offline simulator should be acquirable from the provider."""
    resource = dsl.user.acquires_offline_simulator_resource()

    assert isinstance(resource, OfflineSimulatorResource)


def test_run_native_circuit_on_simulator() -> None:
    """Circuits using the provider's native gates should run successfully on the offline simulator."""
    resource = dsl.user.acquires_offline_simulator_resource()
    circuit = dsl.user.native_circuit()

    result = resource.run(circuit, shots=10).result()

    assert result.success
