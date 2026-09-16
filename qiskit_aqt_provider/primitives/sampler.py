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

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from qiskit.primitives import BackendSamplerV2, BasePrimitiveJob, BaseSamplerV2, PrimitiveResult, SamplerPubResult
from qiskit.primitives.containers.sampler_pub import SamplerPubLike
from qiskit.providers import BackendV2, Options

from qiskit_aqt_provider.aqt_provider import AnyAQTResource
from qiskit_aqt_provider.primitives._transpiling_backend import TranspilingBackend

BackendFactory = Callable[[AnyAQTResource], BackendV2]
SamplerFactory = Callable[[BackendV2, dict[str, Any] | None], BaseSamplerV2]


class AQTSampler(BaseSamplerV2):
    """A sampler primitive for AQT backends."""

    def __init__(self, *, backend: AnyAQTResource, options: dict[str, Any] | None = None) -> None:
        """Initialize the sampler with the given AQT backend."""
        self.backend = backend
        self._options = options or Options()

        self.backend_factory: BackendFactory = TranspilingBackend
        self.sampler_factory: SamplerFactory = lambda b, o: BackendSamplerV2(backend=b, options=o)

    def run(
        self, pubs: Iterable[SamplerPubLike], *, shots: int | None = None
    ) -> BasePrimitiveJob[PrimitiveResult[SamplerPubResult]]:
        """Run the given sampler PUBs on the AQT backend.

        Args:
            pubs (Iterable): An iterable of sampler PUBs, which may include parameterized
                circuits and associated parameter values.
            shots (int | None): The number of shots to use for each circuit. Defaults to None.

        Returns:
            qiskit.primitives.BasePrimitiveJob[qiskit.primitives.PrimitiveResult[qiskit.primitives.SamplerPubResult]]: A
            job representing the execution of the sampler PUBs.
        """
        wrapped_backend = self.backend_factory(self.backend)
        delegate = self.sampler_factory(wrapped_backend, self._options)
        return delegate.run(pubs, shots=shots)
