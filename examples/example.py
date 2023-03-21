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

import qiskit
from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider

if __name__ == "__main__":
    # If no `access_token` is passed to the constructor it is read from
    # the AQT_TOKEN environment variable
    provider = AQTProvider("")

    # The workspaces method returns a list of available workspaces and resources
    print(provider.workspaces())

    # Retrieve a backend by providing a `workspace` and `device_id`
    backend = provider.get_resource("default", "offline_simulator_no_noise")

    # Create a 4-qubit GHZ state
    qc = QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.cx(0, 3)
    qc.measure_all()

    result = qiskit.execute(qc, backend, shots=200).result()

    if result.success:
        print(result.get_counts())
    else:  # pragma: no cover
        print(result.to_dict()["errors"])
