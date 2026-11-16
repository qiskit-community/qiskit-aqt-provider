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

"""Basic example with the Qiskit AQT Arnica provider."""

from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.persistence import FileJobStore

if __name__ == "__main__":
    # Create a store to persist our job
    store = FileJobStore()

    # Use the provider in a context manager to ensure proper cleanup of resources.
    with AQTProvider() as provider:
        # Get the cloud provider interface.
        cloud_provider = provider.cloud()
        # Log in to the cloud provider to establish a session.
        cloud_provider.log_in()

        # Get a workspace provider by its ID.
        workspace = cloud_provider.fetch_workspaces().get_by_id("my-workspace-id")

        # Acquire a backend resource by its ID.
        backend = workspace.get_backend(  # type: ignore[union-attr]
            "my-backend-id"
        )

        # Execute on the target backend.
        qc = QuantumCircuit(2)
        qc.measure_all()
        job = backend.run(qc, shots=200)

        # Persist our job so we can resume it if something goes wrong
        print(f"Submitted job {job.job_id()}")
        job.persist(store=store)

        # Block until the result is ready
        result = job.result()

        if result.success:
            print(result.get_counts())
        else:
            print(result.to_dict()["error"])
