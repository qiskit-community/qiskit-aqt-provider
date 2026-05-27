from qiskit_aer import AerSimulator

from qiskit_aqt_provider._offline_sim.resource import OfflineSimulatorResource, OfflineSimulatorResourceConfig


def test_id_returns_config_name() -> None:
    """The resource's id property should return the name from its configuration."""
    resource = _make_resource(name="my-offline-simulator")

    assert resource.id == "my-offline-simulator"


def test_max_circuits_is_50() -> None:
    """The resource's max_circuits property should return 50."""
    resource = _make_resource()

    assert resource.max_circuits == 50


def test_target_num_qubits() -> None:
    """The resource's target should report the correct number of qubits."""
    resource = _make_resource(num_qubits=5)

    assert resource.target.num_qubits == 5


def test_target_contains_rz_gate() -> None:
    """The resource's target should support the RZ gate."""
    resource = _make_resource()

    assert resource.target.instruction_supported("rz", (0,))


def test_target_contains_r_gate() -> None:
    """The resource's target should support the R gate."""
    resource = _make_resource()

    assert resource.target.instruction_supported("r", (0,))


def test_target_contains_rxx_gate() -> None:
    """The resource's target should support the RXX gate."""
    resource = _make_resource()

    assert resource.target.instruction_supported("rxx", (0, 1))


def test_target_contains_measure() -> None:
    """The resource's target should support the measure instruction."""
    resource = _make_resource()

    assert resource.target.instruction_supported("measure", (0,))


def _make_resource(
    *,
    name: str = "offline-sim",
    num_qubits: int = 2,
) -> OfflineSimulatorResource:
    config = OfflineSimulatorResourceConfig(
        name=name,
        number_of_ions=num_qubits,
        simulator=AerSimulator(method="statevector"),
    )
    return OfflineSimulatorResource(config=config)
