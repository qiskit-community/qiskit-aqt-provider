# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Pytest fixtures for the AQT Qiskit provider.

This module is exposed as pytest plugin for this project.
"""

from typing import Iterator
from unittest.mock import patch

import pytest

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import AQTResource, OfflineSimulatorResource
from qiskit_aqt_provider.circuit_to_aqt import circuit_to_aqt


@pytest.fixture(name="offline_simulator_no_noise")
def fixture_offline_simulator_no_noise() -> Iterator[AQTResource]:
    """Noiseless offline simulator resource."""
    provider = AQTProvider("")
    resource = provider.get_resource("default", "offline_simulator_no_noise")
    with patch.object(OfflineSimulatorResource, "submit", wraps=resource.submit) as mock:
        yield resource

        # try to convert all circuits that were passed to the simulator
        # to the AQT API JSON format.
        for call_args in mock.call_args_list:
            # this could fail if submit() is (partially or fully) called with kwargs
            circuit, shots = call_args.args

            try:
                _ = circuit_to_aqt(circuit, shots=shots)
            except Exception:  # pragma: no cover  # noqa: BLE001
                pytest.fail(f"Circuit cannot be converted to the AQT JSON format:\n{circuit}")
