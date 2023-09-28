# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from typing import Any, Iterator, Mapping, Optional

import pydantic as pdt
from typing_extensions import Self, override


class AQTOptions(
    pdt.BaseModel, Mapping[str, Any], extra=pdt.Extra.forbid, validate_assignment=True
):
    """Options for AQT resources.

    This is a typed drop-in replacement for :class:`qiskit.providers.Options`.

    Options can be set on a backend globally or on a per-job basis. To update an option
    globally, set the corresponding attribute in the backend's
    :attr:`options <qiskit_aqt_provider.aqt_resource.AQTResource.options>` attribute:

    >>> import qiskit
    >>> from qiskit_aqt_provider import AQTProvider
    ...
    >>> backend = AQTProvider("").get_backend("offline_simulator_no_noise")
    ...
    >>> qc = qiskit.QuantumCircuit(1)
    >>> _ = qc.rx(3.14, 0)
    >>> _ = qc.measure_all()
    ...
    >>> backend.options.shots = 50
    >>> result = qiskit.execute(qc, backend).result()
    >>> sum(result.get_counts().values())
    50

    Option overrides can also be applied on a per-job basis, as keyword arguments to
    :func:`qiskit.execute <qiskit.execute_function.execute>` or
    :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>`:

    >>> backend.options.shots
    50
    >>> result = qiskit.execute(qc, backend, shots=100).result()
    >>> sum(result.get_counts().values())
    100
    """

    # Qiskit generic:

    shots: int = pdt.Field(ge=1, le=200, default=100)
    """Number of repetitions per circuit."""

    memory: bool = False
    """Whether to return the sequence of memory states (readout) for each shot.

    See :meth:`qiskit.result.Result.get_memory` for details."""

    # AQT-specific:

    query_period_seconds: float = pdt.Field(ge=0.1, default=1.0)
    """Elapsed time between queries to the cloud portal when waiting for results, in seconds."""

    query_timeout_seconds: Optional[float] = None
    """Maximum time to wait for results of a single job, in seconds."""

    with_progress_bar: bool = True
    """Whether to display a progress bar when waiting for results from a single job.

    When enabled, the progress bar is written to :data:`sys.stderr`."""

    @pdt.validator("query_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value <= 0.0:
            raise ValueError("Timeout must be None or > 0.")

        return value

    def update_options(self, **kwargs: Any) -> Self:
        """Update options by name.

        .. tip::
          This is exposed for compatibility with :class:`qiskit.providers.Options`.
          The preferred way of updating options is by direct (validated)
          assignment.
        """
        update = self.dict()
        update.update(kwargs)

        for key, value in self.validate(update).dict().items():
            setattr(self, key, value)

        return self

    # Mapping[str, Any] implementationm, for compatibility with qiskit.providers.Options

    @override
    def __len__(self) -> int:
        """Number of options."""
        return len(self.__fields__)

    @override
    def __iter__(self) -> Iterator[Any]:  # type: ignore[override]
        """Iterate over option names."""
        return iter(self.__fields__)

    @override
    def __getitem__(self, name: str) -> Any:
        """Get the value for a given option."""
        return self.__dict__[name]
