# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


import io
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from uuid import uuid4

import pytest
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.jobs import RRFinished, RRQueued
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails
from httpx import Client, MockTransport, Response
from qiskit import QuantumCircuit, qpy

from qiskit_aqt_provider._cloud.job import CloudJob
from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata
from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.composite_job import CompositeDirectAccessJob, CompositeDirectAccessJobMetadata
from qiskit_aqt_provider._direct.job import DirectAccessJob, DirectAccessJobMetadata
from qiskit_aqt_provider._direct.resource import DirectAccessResource, DirectAccessResourceConfig
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.exceptions import (
    AQTJobBackendMismatchError,
    AQTJobCorruptError,
    AQTJobIncompatibleError,
    AQTJobNotFoundError,
    AQTJobPersistenceError,
)
from qiskit_aqt_provider.persistence import (
    FileJobStore,
    JobSnapshot,
    decode_job,
    encode_job,
    persist_job,
    restore_job,
)


def _snapshot(*, memory: bool = False) -> JobSnapshot:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return JobSnapshot(uuid4(), "cloud", "r1", 17, memory, [circuit])


def test_qpy_round_trip_preserves_job_metadata_and_circuit() -> None:
    """QPY encoding should preserve metadata and circuit structure."""
    snapshot = _snapshot(memory=True)

    restored = decode_job(encode_job(snapshot))

    assert restored == snapshot
    assert restored.circuits[0] == snapshot.circuits[0]


def test_file_store_overwrites_atomically() -> None:
    """File storage should replace existing records atomically."""
    snapshot = _snapshot()
    with TemporaryDirectory() as directory:
        store = FileJobStore(Path(directory))
        persist_job(snapshot, store)
        first_payload = store.load(str(snapshot.job_id))

        persist_job(snapshot.__class__(snapshot.job_id, "cloud", "r1", 18, True, snapshot.circuits), store)

        assert store.load(str(snapshot.job_id)) != first_payload


def test_file_store_deletes_idempotently() -> None:
    """File storage should tolerate repeated deletion without error."""
    snapshot = _snapshot()
    with TemporaryDirectory() as directory:
        store = FileJobStore(Path(directory))
        persist_job(snapshot, store)
        store.delete(str(snapshot.job_id))
        store.delete(str(snapshot.job_id))


def test_decode_rejects_corrupt_payloads() -> None:
    """The decoder should reject corrupt payloads."""
    with pytest.raises(AQTJobCorruptError):
        decode_job(b"not a job")


def test_decode_rejects_incompatible_payload() -> None:
    """The decoder should reject payloads with unsupported format versions."""
    with pytest.raises(AQTJobIncompatibleError):
        decode_job(b'{"format_version":99}\n')


def test_decode_rejects_empty_circuit_payload() -> None:
    """The decoder should reject a valid QPY payload containing no circuits."""
    circuit_data = io.BytesIO()
    qpy.dump([], circuit_data)
    header = {
        "format_version": 1,
        "job_id": str(uuid4()),
        "backend_kind": "cloud",
        "backend_name": "r1",
        "shots": 1,
        "memory": False,
        "circuit_count": 0,
    }

    with pytest.raises(AQTJobCorruptError):
        decode_job(json.dumps(header).encode("utf-8") + b"\n" + circuit_data.getvalue())


def test_missing_arbitrary_store_key_is_not_found() -> None:
    """Missing non-UUID keys should still produce the not-found error."""
    with TemporaryDirectory() as directory:
        with pytest.raises(AQTJobNotFoundError):
            FileJobStore(Path(directory)).load("missing")


def test_cloud_job_can_be_restored_by_a_matching_resource() -> None:
    """A cloud resource should restore the circuit and options from persisted data."""
    snapshot = _snapshot(memory=True)
    details = ResourceDetails(
        id="r1",
        name="r1",
        type=ResourceType.DEVICE,
        status=ResourceStatus.ONLINE,
        available_qubits=2,
        status_updated_at=datetime(2026, 1, 1),
    )
    client = Client(transport=MockTransport(lambda _: Response(404)))
    resource = CloudResource(ArnicaApp(), client, "w1", details)
    job = CloudJob(
        ArnicaApp(),
        client,
        CloudJobMetadata(
            job_id=snapshot.job_id,
            shots=snapshot.shots,
            backend_name=snapshot.backend_name,
            circuits=snapshot.circuits,
            initial_state=RRQueued(),
            memory=snapshot.memory,
        ),
    )

    with TemporaryDirectory() as directory:
        store = FileJobStore(Path(directory))
        job.persist(store=store)
        restored = resource.restore_job(job.job_id(), store=store)

        assert restored.job_id() == job.job_id()
        assert restored._properties.circuits == job._properties.circuits
        assert restored._properties.memory is True


def test_cloud_job_honours_memory_option_when_building_result() -> None:
    """Cloud result conversion should include per-shot memory when requested."""
    snapshot = _snapshot(memory=True)
    job = CloudJob(
        ArnicaApp(),
        Client(transport=MockTransport(lambda _: Response(404))),
        CloudJobMetadata(
            job_id=snapshot.job_id,
            shots=2,
            backend_name=snapshot.backend_name,
            circuits=[snapshot.circuits[0]],
            initial_state=RRFinished(result={0: [[0, 0], [1, 1]]}),
            memory=True,
        ),
    )

    result = job.result()

    assert result.get_memory() == ["00", "11"]


def test_restore_rejects_a_different_backend() -> None:
    """Restoration should reject a record belonging to another backend kind."""
    snapshot = _snapshot()
    store = mock.Mock()
    store.load.return_value = encode_job(snapshot)

    with pytest.raises(AQTJobBackendMismatchError):
        restore_job(str(snapshot.job_id), store=store, backend_kind="direct", backend_name="r1")

    store.delete.assert_not_called()


def test_direct_job_can_be_restored() -> None:
    """Direct single jobs should be restorable from persisted data."""
    snapshot = _snapshot(memory=True)
    client = mock.Mock(spec=DirectAccessAPIClient)
    resource = DirectAccessResource(DirectAccessResourceConfig("r1", 2, client))
    job = DirectAccessJob(
        client,
        snapshot.job_id,
        DirectAccessJobMetadata("r1", snapshot.shots, snapshot.circuits[0], snapshot.memory),
    )

    with TemporaryDirectory() as directory:
        store = FileJobStore(Path(directory))
        job.persist(store=store)
        restored = resource.restore_job(job.job_id(), store=store, delete=True)

        assert restored.job_id() == job.job_id()
        assert restored._metadata.circuit == job._metadata.circuit
        assert restored._metadata.memory is True
        client.await_result.return_value = api_models_direct.JobResult.create_finished(
            job_id=snapshot.job_id, result=[[0, 0], [1, 1]]
        ).payload
        assert restored.result().get_memory() == ["00", "11"]
        with pytest.raises(AQTJobNotFoundError):
            store.load(job.job_id())


def test_composite_direct_jobs_cannot_be_persisted() -> None:
    """Composite direct access jobs should not be allowed to persist."""
    composite = CompositeDirectAccessJob(CompositeDirectAccessJobMetadata(backend_name="r1"), [])
    with pytest.raises(AQTJobPersistenceError, match="single-circuit"):
        composite.persist()
