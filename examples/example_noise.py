# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Basic example with the Qiskit AQT provider and the noisy offline simulator.

Creates a 2-qubit GHZ state.
"""


import qiskit
from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider

if __name__ == "__main__":
    # If no `access_token` is passed to the constructor it is read from
    # the AQT_TOKEN environment variable
    provider = AQTProvider("token")

    # The backends() method lists all available computing backends. Printing it
    # renders it as a table that shows each backend's containing workspace.
    print(provider.backends())

    # Retrieve a backend by providing search criteria. The search must have a single
    # match. For example:
    backend = provider.get_backend("offline_simulator_noise", workspace="default")

    # Create a 2-qubit GHZ state
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    result = qiskit.execute(qc, backend, shots=200).result()

    if result.success:
        # due to the noise, also the states '01' and '10' may be populated!
        print(result.get_counts())
    else:  # pragma: no cover
        print(result.to_dict()["error"])
