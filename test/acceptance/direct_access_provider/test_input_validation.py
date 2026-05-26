import pytest
from qiskit import QuantumCircuit

from test.acceptance import dsl
from test.acceptance.conftest import DummyDirectAccessServer


def test_empty_circuits_are_rejected(direct_access_api: DummyDirectAccessServer) -> None:
    """Empty circuits should be rejected.

    Given a circuit with no measurement operations
    When it is submitted to a direct-access backend
    Then submission is rejected as invalid input
    """
    with pytest.raises(ValueError, match="Circuit must have at least one measurement operation"):
        dsl.user.submits_direct_access_circuit(direct_access_api.base_url, "direct_token", QuantumCircuit(1))


def test_circuits_with_non_native_operations_are_rejected(direct_access_api: DummyDirectAccessServer) -> None:
    """Circuits with operations that are not in the native gate set should be rejected.

    Given a circuit using a non-native operation
    When it is submitted to a direct-access backend
    Then submission is rejected with a basis-gate validation error
    """
    with pytest.raises(ValueError, match="not in basis gate set"):
        dsl.user.submits_direct_access_circuit(
            direct_access_api.base_url,
            "direct_token",
            dsl.user.non_native_circuit(),
        )


def test_circuits_with_parametrised_operations_are_rejected(
    direct_access_api: DummyDirectAccessServer,
) -> None:
    """Circuits with parametrised operations should be rejected.

    Given a circuit with unbound symbolic parameters
    When it is submitted to a direct-access backend
    Then submission is rejected before API submission
    """
    with pytest.raises(TypeError):
        dsl.user.submits_direct_access_circuit(
            direct_access_api.base_url,
            "direct_token",
            dsl.user.parametrised_circuit(),
        )
