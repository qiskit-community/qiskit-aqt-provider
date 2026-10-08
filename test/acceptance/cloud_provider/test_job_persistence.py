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
from aqt_connector import ArnicaConfig
from qiskit import QuantumCircuit

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.exceptions import AQTJobNotFoundError
from qiskit_aqt_provider.persistence import FileJobStore
from test.acceptance import dsl
from test.acceptance.conftest import DummyArnicaServer


def _persist_cloud_job(
    monkeypatch: pytest.MonkeyPatch,
    dummy_cloud_server: DummyArnicaServer,
    tmp_path: Path,
) -> tuple[ArnicaConfig, Path, str]:
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    monkeypatch.setattr(
        "aqt_connector._domain.auth_service.AuthService.get_or_refresh_access_token",
        lambda _self, _store: "arnica_token",
    )
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_cloud_server.base_url
    store_path = tmp_path / "jobs"

    first_circuit = QuantumCircuit(1)
    first_circuit.measure_all()
    second_circuit = QuantumCircuit(2)
    second_circuit.measure_all()

    with AQTProvider() as provider:
        workspace = provider.cloud(cloud_provider_config).fetch_workspaces().get_by_id("w1")
        assert workspace is not None
        backend = workspace.get_backend("r1")
        job = backend.run([first_circuit, second_circuit], shots=3, memory=True)
        job_id = job.job_id()
        job.persist(store=FileJobStore(store_path))

    return cloud_provider_config, store_path, job_id


def test_cloud_job_can_be_persisted_and_restored(
    monkeypatch: pytest.MonkeyPatch,
    dummy_cloud_server: DummyArnicaServer,
    tmp_path: Path,
) -> None:
    """A persisted cloud job can be restored through a newly configured provider."""
    cloud_provider_config, store_path, job_id = _persist_cloud_job(monkeypatch, dummy_cloud_server, tmp_path)

    with AQTProvider() as provider:
        workspace = provider.cloud(cloud_provider_config).fetch_workspaces().get_by_id("w1")
        assert workspace is not None
        backend = workspace.get_backend("r1")
        restored_job = backend.restore_job(job_id, store=FileJobStore(store_path))
        result = restored_job.result()

        assert restored_job.job_id() == job_id
        assert result.get_counts(0) == {"0": 1, "1": 2}
        assert result.get_counts(1) == {"01": 2, "10": 1}
        assert result.get_memory(0) == ["0", "1", "1"]
        assert result.get_memory(1) == ["01", "10", "01"]


def test_cloud_job_can_be_deleted_during_restore(
    monkeypatch: pytest.MonkeyPatch,
    dummy_cloud_server: DummyArnicaServer,
    tmp_path: Path,
) -> None:
    """A persisted cloud job can be deleted while it is restored."""
    cloud_provider_config, store_path, job_id = _persist_cloud_job(monkeypatch, dummy_cloud_server, tmp_path)
    store = FileJobStore(store_path)

    with AQTProvider() as provider:
        workspace = provider.cloud(cloud_provider_config).fetch_workspaces().get_by_id("w1")
        assert workspace is not None
        backend = workspace.get_backend("r1")
        backend.restore_job(job_id, store=store, delete=True)

    with pytest.raises(AQTJobNotFoundError):
        store.load(job_id)
