from test.acceptance import dsl
from test.acceptance.conftest import DummyDirectAccessServer


def test_direct_access_backend_acquisition(direct_access_api: DummyDirectAccessServer) -> None:
    """Direct access backends should be acquirable from the provider.

    Given a user with direct access credentials and a reachable direct API endpoint
    When they acquire a direct access backend from the provider
    Then they receive a backend with the expected identity and target capabilities
    """
    dsl.user.has_access_to_direct_access_resource(direct_access_api, name="direct-r1", qubits=6)

    backend = dsl.user.acquires_direct_access_backend(direct_access_api.base_url, "direct_token")

    assert backend.name == "direct-r1"
    assert backend.target.num_qubits == 6
