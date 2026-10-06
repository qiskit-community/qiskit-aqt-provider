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


from pathlib import Path

import pytest
from qiskit.result import Result

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.api_client.models_direct import JobResultFinished
from qiskit_aqt_provider.exceptions import AQTJobNotFoundError, AQTJobPersistenceError
from qiskit_aqt_provider.persistence import FileJobStore
from test.acceptance import dsl
from test.acceptance.conftest import DummyDirectAccessServer


def _persist_direct_job(direct_access_api: DummyDirectAccessServer, tmp_path: Path) -> tuple[Path, str]:
    store_path = tmp_path / "jobs"

    with AQTProvider() as provider:
        backend = provider.direct_access().get_resource(direct_access_api.base_url, "direct_token")
        job = backend.run(dsl.user.native_circuit(), shots=3, memory=True)
        job_id = job.job_id()
        job.persist(store=FileJobStore(store_path))

    return store_path, job_id


def test_direct_job_can_be_persisted_and_restored(direct_access_api: DummyDirectAccessServer, tmp_path: Path) -> None:
    """A persisted single-circuit direct job can be restored after provider recreation."""
    store_path, job_id = _persist_direct_job(direct_access_api, tmp_path)

    dsl.direct_access_resource.will_return_results(direct_access_api, [JobResultFinished(result=[[0], [1], [1]])])

    with AQTProvider() as provider:
        backend = provider.direct_access().get_resource(direct_access_api.base_url, "direct_token")
        restored_job = backend.restore_job(job_id, store=FileJobStore(store_path))
        result = restored_job.result()

        assert isinstance(result, Result)
        assert restored_job.job_id() == job_id
        assert result.get_counts() == {"0": 1, "1": 2}
        assert result.get_memory() == ["0", "1", "1"]


def test_direct_job_can_be_deleted_during_restore(direct_access_api: DummyDirectAccessServer, tmp_path: Path) -> None:
    """A persisted single-circuit direct job can be deleted while it is restored."""
    store_path, job_id = _persist_direct_job(direct_access_api, tmp_path)
    store = FileJobStore(store_path)

    with AQTProvider() as provider:
        backend = provider.direct_access().get_resource(direct_access_api.base_url, "direct_token")
        backend.restore_job(job_id, store=store, delete=True)

    with pytest.raises(AQTJobNotFoundError):
        store.load(job_id)


def test_direct_composite_job_persistence_is_not_supported(
    direct_access_api: DummyDirectAccessServer, tmp_path: Path
) -> None:
    """Lazy composite direct jobs explain why they cannot be persisted."""
    with AQTProvider() as provider:
        backend = provider.direct_access().get_resource(direct_access_api.base_url, "direct_token")
        job = backend.run([dsl.user.native_circuit(), dsl.user.native_circuit()])

        with pytest.raises(AQTJobPersistenceError, match="single-circuit direct jobs"):
            job.persist(store=FileJobStore(tmp_path / "jobs"))
