"""Basic example with the Qiskit AQT Arnica provider."""

from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider

if __name__ == "__main__":
    # Use the provider in a context manager to ensure proper cleanup of resources.
    with AQTProvider() as provider:
        cloud_provider = provider.cloud()  # Get the cloud provider interface.
        cloud_provider.log_in()  # Log in to the cloud provider to establish a session.
        workspaces = cloud_provider.fetch_workspaces()
        workspace = workspaces.get_by_id("my-workspace-id")  # Get a workspace provider by its ID.
        backend = workspace.get_backend("my-backend-id")  # Acquire a backend resource by its ID.

        qc = QuantumCircuit(2)
        qc.measure_all()

        # Execute on the target backend.
        result = backend.run(qc, shots=200).result()

        if result.success:
            print(result.get_counts())
        else:  # pragma: no cover
            print(result.to_dict()["error"])
