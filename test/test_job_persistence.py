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

import json
import os
import re
import uuid
from pathlib import Path
from typing import NamedTuple, Optional

import httpx
import pytest
import qiskit
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture
from qiskit.providers import JobStatus

from qiskit_aqt_provider import persistence
from qiskit_aqt_provider.api_client import Resource
from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.api_client import models_generated as api_models_generated
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_options import AQTOptions
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import AQTResource, OfflineSimulatorResource
from qiskit_aqt_provider.test.circuits import random_circuit
from qiskit_aqt_provider.test.fixtures import MockSimulator


@pytest.mark.parametrize(
    "backend_name",
    [
        "offline_simulator_no_noise",
        pytest.param(
            "offline_simulator_noise",
            marks=pytest.mark.xfail(reason="Job persistence on noisy simulator not supported."),
        ),
    ],
)
@pytest.mark.parametrize("remove_from_store", [True, False])
def test_job_persistence_transaction_offline_simulator(
    backend_name: str, remove_from_store: bool, tmp_path: Path
) -> None:
    """Persist and restore a job on offline simulators."""
    token = str(uuid.uuid4())
    provider = AQTProvider(token)
    backend = provider.get_backend(backend_name)
    assert isinstance(backend, OfflineSimulatorResource)

    circuits = [random_circuit(2), random_circuit(3)]
    job = backend.run(qiskit.transpile(circuits, backend))

    path = job.persist(store_path=tmp_path)

    # sanity check
    assert str(path).startswith(str(tmp_path))

    restored_job = AQTJob.restore(
        job.job_id(), access_token=token, store_path=tmp_path, remove_from_store=remove_from_store
    )

    assert path.exists() is not remove_from_store

    assert isinstance(restored_job.backend(), OfflineSimulatorResource)
    restored_backend: OfflineSimulatorResource = restored_job.backend()

    assert restored_backend.provider.access_token == backend.provider.access_token
    assert restored_backend.with_noise_model == backend.with_noise_model

    assert restored_job.options == job.options
    assert restored_job.circuits == job.circuits
    assert restored_job.api_submit_payload == job.api_submit_payload

    # for offline simulators, the backend state is fully lost so the restored_job
    # is actually a new one
    assert restored_job.job_id()
    assert restored_job.job_id() != job.job_id()

    # we get a result for both jobs, but they in principle differ because the job was re-submitted
    assert restored_job.result().success
    assert len(restored_job.result().get_counts()) == len(circuits)
    assert job.result().success
    assert len(job.result().get_counts()) == len(circuits)


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_job_persistence_transaction_online_backend(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Persist and restore a job on mocked online resources."""
    # Set up a fake online resource
    token = str(uuid.uuid4())
    provider = AQTProvider(token)
    resource_id = Resource(
        workspace_id=str(uuid.uuid4()),
        resource_id=str(uuid.uuid4()),
        resource_name=str(uuid.uuid4()),
        resource_type="device",
    )
    backend = AQTResource(provider, resource_id)

    class PortalJob(NamedTuple):
        """Mocked portal state: holds details of the submitted jobs."""

        circuits: list[api_models_generated.QuantumCircuit]
        workspace_id: str
        resource_id: str
        error_msg: str

    portal_state: dict[uuid.UUID, PortalJob] = {}

    def handle_submit(request: httpx.Request) -> httpx.Response:
        """Mocked circuit submission endpoint.

        Create a job ID and a unique error message for the submitted job.
        Store the details in `portal_state`.
        """
        assert request.headers["authorization"] == f"Bearer {token}"

        _, workspace_id, resource_id = request.url.path.rsplit("/", maxsplit=2)
        data = api_models.SubmitJobRequest.model_validate_json(request.content.decode("utf-8"))
        circuits = data.payload.circuits
        job_id = uuid.uuid4()

        assert job_id not in portal_state
        portal_state[job_id] = PortalJob(
            circuits=circuits,
            workspace_id=workspace_id,
            resource_id=resource_id,
            error_msg=str(uuid.uuid4()),
        )

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.queued(
                    job_id=job_id, resource_id=resource_id, workspace_id=workspace_id
                ).model_dump_json()
            ),
        )

    def handle_result(request: httpx.Request) -> httpx.Response:
        """Mocked circuit result endpoint.

        Check that the access token is valid.
        Return an error response, with the unique error message for the
        requested job ID.
        """
        assert request.headers["authorization"] == f"Bearer {token}"

        _, job_id = request.url.path.rsplit("/", maxsplit=1)
        job = portal_state[uuid.UUID(job_id)]

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.error(
                    job_id=uuid.UUID(job_id),
                    workspace_id=job.workspace_id,
                    resource_id=job.resource_id,
                    message=job.error_msg,
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(
        handle_submit, url=re.compile(r".+/submit/[0-9a-f-]+/[0-9a-f-]+$"), method="POST"
    )
    httpx_mock.add_callback(handle_result, url=re.compile(r".+/result/[0-9a-f-]+$"), method="GET")

    # ----------

    circuits = [random_circuit(2), random_circuit(3), random_circuit(4)]
    job = backend.run(qiskit.transpile(circuits, backend), shots=123)

    # sanity checks
    assert uuid.UUID(job.job_id()) in portal_state
    assert job.options != AQTOptions()  # non-default options because shots=123

    path = job.persist(store_path=tmp_path)
    restored_job = AQTJob.restore(job.job_id(), access_token=token, store_path=tmp_path)

    assert not path.exists()  # remove_from_store is True by default

    assert restored_job.job_id() == job.job_id()
    assert restored_job.circuits == job.circuits
    assert restored_job.options == job.options

    # the mocked GET /result route always returns an error response with a unique error message
    assert job.status() is JobStatus.ERROR
    assert restored_job.status() is JobStatus.ERROR

    assert job.error_message
    assert job.error_message == restored_job.error_message

    assert job.result().success is False
    assert restored_job.result().success is False

    # both job and restored_job have already been submitted, so they can't be submitted again
    with pytest.raises(RuntimeError, match="Job already submitted"):
        job.submit()

    with pytest.raises(RuntimeError, match="Job already submitted"):
        restored_job.submit()


def test_can_only_persist_submitted_jobs(
    offline_simulator_no_noise: MockSimulator, tmp_path: Path
) -> None:
    """Check that only jobs with a valid job_id can be persisted."""
    circuit = qiskit.transpile(random_circuit(2), offline_simulator_no_noise)
    job = AQTJob(offline_simulator_no_noise, [circuit], AQTOptions())

    assert not job.job_id()
    with pytest.raises(RuntimeError, match=r"Can only persist submitted jobs."):
        job.persist(store_path=tmp_path)


def test_restore_unknown_job(tmp_path: Path) -> None:
    """Check that an attempt at restoring an unknown job raises JobNotFoundError."""
    with pytest.raises(persistence.JobNotFoundError):
        AQTJob.restore(job_id="invalid", store_path=tmp_path)


@pytest.mark.parametrize("override", [None, Path("foo/bar")])
def test_store_path_resolver(
    override: Optional[Path], tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test the persistence store path resolver.

    The returned path must:
    - be the override, if passed
    - exist
    - be a directory.
    """
    # do not pollute the test user's environment
    # this only works on unix
    mocker.patch.dict(os.environ, {"XDG_CACHE_HOME": str(tmp_path)})

    if override is not None:
        override = tmp_path / override

    store_path = persistence.get_store_path(override)

    # sanity check: make sure the mock works
    assert str(store_path).startswith(str(tmp_path))

    assert store_path.exists()
    assert store_path.is_dir()

    if override is not None:
        assert store_path == override
