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
