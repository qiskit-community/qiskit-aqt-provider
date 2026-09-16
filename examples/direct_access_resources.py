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

if __name__ == "__main__":
    # Use the provider in a context manager to ensure proper cleanup of resources.
    with AQTProvider() as provider:
        direct_access_provider = provider.direct_access()
        # Use the direct access provider to get a backend instance for a specific resource, providing the base URL
        # and access token for authentication:
        backend = direct_access_provider.get_resource("http://example.com", "my-super-secret-token")

        qc = QuantumCircuit(2)
        qc.measure_all()

        # Execute on the target backend.
        result = backend.run(qc, shots=200).result()

        if result.success:
            print(result.get_counts())
        else:  # pragma: no cover
            print(result.to_dict()["error"])
