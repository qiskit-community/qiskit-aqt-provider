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

from qiskit_aqt_provider.api_client import models_direct
from test.acceptance.conftest import DummyDirectAccessServer


def will_return_results(
    dummy_direct_access_server: DummyDirectAccessServer,
    results: list[models_direct.JobResultError | models_direct.JobResultFinished],
    *,
    result_delay_seconds: float = 0.0,
) -> None:
    """A direct-access resource successfully processes a submitted circuit and returns the expected result.

    Args:
        dummy_direct_access_server (DummyDirectAccessServer): The fixture for the dummy direct access server.
        results (list[models_direct.JobResultError | models_direct.JobResultFinished]): The results to be returned by
            the dummy server for the submitted circuit.
        result_delay_seconds (float, optional): The number of seconds to delay before returning the result. Defaults to
            0.0.
    """
    dummy_direct_access_server.configure_direct_access(
        queued_results=[result.model_dump() for result in results],
        result_delay_seconds=result_delay_seconds,
    )
