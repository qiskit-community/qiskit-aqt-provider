from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from unittest import mock

from qiskit import QuantumCircuit
from qiskit.primitives import BaseEstimatorV2
from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
from qiskit.providers import BackendV2

from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.aqt_provider import AnyAQTResource
from qiskit_aqt_provider.primitives._transpiling_backend import TranspilingBackend
from qiskit_aqt_provider.primitives.estimator import AQTEstimator


class _RecordingEstimatorDelegate(BaseEstimatorV2):
    def __init__(self, *, returned_job: object) -> None:
        self.returned_job = returned_job
        self.calls: list[dict[str, Any]] = []

    def run(self, pubs: Iterable[EstimatorPubLike], *, precision: float | None = None) -> object:
        self.calls.append({"pubs": pubs, "precision": precision})
        return self.returned_job


def test_run_uses_injected_factories_and_forwards_precision() -> None:
    """Estimator should collaborate through DI hooks and forward run arguments."""
    backend = mock.Mock(spec=CloudResource, name="aqt_backend")
    wrapped_backend = mock.Mock(spec=TranspilingBackend, name="wrapped_backend")
    returned_job = mock.Mock(name="estimator_job")

    estimator = AQTEstimator(backend=backend, options={"shots": 123})

    seen: dict[str, Any] = {}

    def backend_factory(received_backend: AnyAQTResource) -> BackendV2:
        seen["backend"] = received_backend
        return wrapped_backend

    delegate = _RecordingEstimatorDelegate(returned_job=returned_job)

    def estimator_factory(
        received_wrapped_backend: BackendV2, received_options: dict[str, Any] | None
    ) -> _RecordingEstimatorDelegate:
        seen["wrapped_backend"] = received_wrapped_backend
        seen["options"] = received_options
        return delegate

    estimator.backend_factory = backend_factory
    estimator.estimator_factory = estimator_factory

    pubs: list[EstimatorPubLike] = [(QuantumCircuit(1), "Z")]
    result = estimator.run(pubs, precision=0.125)

    assert result is returned_job
    assert seen["backend"] is backend
    assert seen["wrapped_backend"] is wrapped_backend
    assert seen["options"] == {"shots": 123}
    assert delegate.calls == [{"pubs": pubs, "precision": 0.125}]


def test_run_passes_none_precision_by_default() -> None:
    """Estimator should call delegate with precision=None when not provided."""
    estimator = AQTEstimator(backend=mock.Mock(spec=CloudResource, name="aqt_backend"))
    delegate = _RecordingEstimatorDelegate(returned_job=mock.Mock(name="estimator_job"))

    estimator.backend_factory = lambda _backend: mock.Mock(spec=TranspilingBackend, name="wrapped_backend")
    estimator.estimator_factory = lambda _wrapped, _options: delegate

    pubs: list[EstimatorPubLike] = [(QuantumCircuit(1), "Z")]
    estimator.run(pubs)

    assert delegate.calls == [{"pubs": pubs, "precision": None}]
