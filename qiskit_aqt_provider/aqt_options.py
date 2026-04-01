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

from collections.abc import Iterator, Mapping
from typing import Any, Optional

import annotated_types
import pydantic as pdt
from typing_extensions import Self, override


class AQTOptions(pdt.BaseModel, Mapping[str, Any]):
    """Options for AQT resources.

    This is a typed drop-in replacement for :class:`qiskit.providers.Options`.

    Options can be set on a backend globally or on a per-job basis. To update an option
    globally, set the corresponding attribute in the backend's
    :attr:`options <qiskit_aqt_provider.aqt_resource._ResourceBase.options>` attribute:

    >>> import qiskit
    >>> from qiskit_aqt_provider import AQTProvider
    >>>
    >>> backend = AQTProvider("").get_backend("offline_simulator_no_noise")
    >>>
    >>> qc = qiskit.QuantumCircuit(1)
    >>> _ = qc.rx(3.14, 0)
    >>> _ = qc.measure_all()
    >>> qc = qiskit.transpile(qc, backend)
    >>>
    >>> backend.options.shots = 50
    >>> result = backend.run(qc).result()
    >>> sum(result.get_counts().values())
    50

    Option overrides can also be applied on a per-job basis, as keyword arguments to
    :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>` or
    :meth:`AQTDirectAccessResource.run
    <qiskit_aqt_provider.aqt_resource.AQTDirectAccessResource.run>`:

    >>> backend.options.shots
    50
    >>> result = backend.run(qc, shots=100).result()
    >>> sum(result.get_counts().values())
    100
    """

    model_config = pdt.ConfigDict(extra="forbid", validate_assignment=True)

    # Qiskit generic:

    shots: int = pdt.Field(ge=1, le=2000, default=100)
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

    When enabled, the progress bar is written to :data:`sys.stderr`.
    """

    @pdt.field_validator("query_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: Optional[float], info: pdt.ValidationInfo) -> Optional[float]:
        """Enforce that the timeout, if set, is strictly positive."""
        if value is not None and value <= 0.0:
            raise ValueError(f"{info.field_name} must be None or > 0.")

        return value

    def update_options(self, **kwargs: Any) -> Self:
        """Update options by name.

        .. tip::
          This is exposed for compatibility with :class:`qiskit.providers.Options`.
          The preferred way of updating options is by direct (validated)
          assignment.
        """
        update = self.model_dump()
        update.update(kwargs)

        for key, value in self.model_validate(update).model_dump().items():
            setattr(self, key, value)

        return self

    # Mapping[str, Any] implementation, for compatibility with qiskit.providers.Options

    @override
    def __len__(self) -> int:
        """Number of options."""
        return len(self.model_fields)

    @override
    def __iter__(self) -> Iterator[Any]:  # type: ignore[override]
        """Iterate over option names."""
        return iter(self.model_fields)

    @override
    def __getitem__(self, name: str) -> Any:
        """Get the value for a given option."""
        return self.__dict__[name]

    # Convenience methods

    @classmethod
    def max_shots(cls) -> int:
        """Maximum number of repetitions per circuit."""
        for metadata in cls.model_fields["shots"].metadata:
            if isinstance(metadata, annotated_types.Le):
                return int(str(metadata.le))

            if isinstance(metadata, annotated_types.Lt):  # pragma: no cover
                return int(str(metadata.lt)) - 1

        raise ValueError("No upper bound found for 'shots'.")  # pragma: no cover


class AQTDirectAccessOptions(AQTOptions):
    """Options for AQT direct-access resources."""

    shots: int = pdt.Field(ge=1, le=200, default=100)
    """Number of repetitions per circuit."""
