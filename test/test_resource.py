# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import math
from unittest import mock

import pytest
from qiskit import QuantumCircuit
from qiskit.providers.exceptions import JobTimeoutError

from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import (
    ApiResource,
    AQTResource,
    OfflineSimulatorResource,
)
from qiskit_aqt_provider.test.resources import TestResource


def test_options_set_query_timeout(offline_simulator_no_noise: AQTResource) -> None:
    """Set the query timeout for job status queries with different values."""

    backend = offline_simulator_no_noise

    # works with integers
    backend.options.update_options(query_timeout_seconds=123)
    assert backend.options.query_timeout_seconds == 123

    # works with floats
    backend.options.update_options(query_timeout_seconds=123.45)
    assert backend.options.query_timeout_seconds == 123.45

    # works with None (no timeout)
    backend.options.update_options(query_timeout_seconds=None)
    assert backend.options.query_timeout_seconds is None

    # doesn't work with str
    with pytest.raises(TypeError):
        backend.options.update_options(query_timeout_seconds="abc")


def test_options_set_query_period(offline_simulator_no_noise: AQTResource) -> None:
    """Set the query period for job status queries with different values."""

    backend = offline_simulator_no_noise

    # works with integers
    backend.options.update_options(query_period_seconds=123)
    assert backend.options.query_period_seconds == 123

    # works with floats
    backend.options.update_options(query_period_seconds=123.45)
    assert backend.options.query_period_seconds == 123.45

    # doesn't work with None
    with pytest.raises(TypeError):
        backend.options.update_options(query_period_seconds=None)

    # doesn't work with str
    with pytest.raises(TypeError):
        backend.options.update_options(query_period_seconds="abc")


def test_query_timeout_propagation() -> None:
    """Check that the query timeout is properly propagated from the backend options to
    the job result polling loop.

    Acquire a resource with 10s processing time, but set the job result timeout to 1s.
    Check that calling `result()` on the job handle fails with a timeout error."""
    response_delay = 10.0
    timeout = 1.0
    assert timeout < response_delay

    backend = TestResource(min_running_duration=response_delay)
    backend.options.update_options(query_timeout_seconds=timeout, query_period_seconds=0.5)

    qc = QuantumCircuit(1)
    qc.rx(3.14, 0)

    job = backend.run(qc)

    with pytest.raises(JobTimeoutError):
        job.result()


def test_query_period_propagation() -> None:
    """Check that the query wait duration is properly propagated from the backend options
    to the job result polling loop.

    Set the polling period (much) shorter than the backend's processing time. Check that
    the backend is polled the calculated number of times."""
    response_delay = 2.0
    period_seconds = 0.5
    timeout_seconds = 3.0
    assert timeout_seconds > response_delay  # won't time out

    backend = TestResource(min_running_duration=response_delay)
    backend.options.update_options(
        query_timeout_seconds=timeout_seconds, query_period_seconds=period_seconds
    )

    qc = QuantumCircuit(1)
    qc.rx(3.14, 0)
    qc.measure_all()

    job = backend.run(qc)

    with mock.patch.object(AQTJob, "status", wraps=job.status) as mocked_status:
        job.result()

    lower_bound = math.floor(response_delay / period_seconds)
    upper_bound = math.ceil(response_delay / period_seconds) + 1
    assert lower_bound <= mocked_status.call_count <= upper_bound


def test_offline_simulator_invalid_api_resource() -> None:
    """Check that one cannot instantiate an OfflineSimulatorResource on an API resource
    that is no offline simulator."""
    with pytest.raises(ValueError):
        OfflineSimulatorResource(
            AQTProvider(""),
            "default",
            ApiResource(name="dummy", id="dummy", type="device"),
        )
