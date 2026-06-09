from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from unittest import mock

from qiskit import QuantumCircuit
from qiskit.primitives.containers.sampler_pub import SamplerPubLike
from qiskit.providers import BackendV2, Options

from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.aqt_provider import AnyAQTResource
from qiskit_aqt_provider.primitives._transpiling_backend import TranspilingBackend
from qiskit_aqt_provider.primitives.sampler import AQTSampler


class _RecordingSamplerDelegate:
    def __init__(self, *, returned_job: object) -> None:
        self.returned_job = returned_job
        self.calls: list[dict[str, Any]] = []

    def run(self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None) -> object:
        self.calls.append({"pubs": pubs, "shots": shots})
        return self.returned_job


def test_run_uses_injected_factories_and_forwards_shots() -> None:
    """Sampler should collaborate through DI hooks and forward run arguments."""
    backend = mock.Mock(spec=CloudResource, name="aqt_backend")
    wrapped_backend = mock.Mock(spec=TranspilingBackend, name="wrapped_backend")
    returned_job = mock.Mock(name="sampler_job")

    sampler = AQTSampler(backend=backend, options={"seed": 7})

    seen: dict[str, Any] = {}

    def backend_factory(received_backend: AnyAQTResource) -> BackendV2:
        seen["backend"] = received_backend
        return wrapped_backend

    delegate = _RecordingSamplerDelegate(returned_job=returned_job)

    def sampler_factory(
        received_wrapped_backend: BackendV2, received_options: dict[str, Any] | Options
    ) -> _RecordingSamplerDelegate:
        seen["wrapped_backend"] = received_wrapped_backend
        seen["options"] = received_options
        return delegate

    sampler.backend_factory = backend_factory
    sampler.sampler_factory = sampler_factory

    circuit = QuantumCircuit(1)
    circuit.measure_all()
    pubs: list[SamplerPubLike] = [circuit]
    result = sampler.run(pubs, shots=512)

    assert result is returned_job
    assert seen["backend"] is backend
    assert seen["wrapped_backend"] is wrapped_backend
    assert seen["options"] == {"seed": 7}
    assert delegate.calls == [{"pubs": pubs, "shots": 512}]


def test_run_passes_none_shots_by_default() -> None:
    """Sampler should call delegate with shots=None when not provided."""
    sampler = AQTSampler(backend=mock.Mock(spec=CloudResource, name="aqt_backend"))
    delegate = _RecordingSamplerDelegate(returned_job=mock.Mock(name="sampler_job"))

    sampler.backend_factory = lambda _backend: mock.Mock(spec=TranspilingBackend, name="wrapped_backend")
    sampler.sampler_factory = lambda _wrapped, _options: delegate

    circuit = QuantumCircuit(1)
    circuit.measure_all()
    pubs: list[SamplerPubLike] = [circuit]
    sampler.run(pubs)

    assert delegate.calls == [{"pubs": pubs, "shots": None}]
