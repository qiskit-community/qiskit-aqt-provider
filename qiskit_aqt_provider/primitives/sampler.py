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

from copy import copy
from typing import Any, Optional

from qiskit.primitives import BackendSampler

from qiskit_aqt_provider import transpiler_plugin
from qiskit_aqt_provider.aqt_resource import AnyAQTResource, make_transpiler_target


class AQTSampler(BackendSampler):
    """:class:`BaseSamplerV1 <qiskit.primitives.BaseSamplerV1>` primitive for AQT backends."""

    _backend: AnyAQTResource

    def __init__(
        self,
        backend: AnyAQTResource,
        options: Optional[dict[str, Any]] = None,
        skip_transpilation: bool = False,
    ) -> None:
        """Initialize a ``Sampler`` primitive using an AQT backend.

        Args:
            backend: AQT resource to evaluate circuits on.
            options: options passed through to the underlying
              :class:`BackendSampler <qiskit.primitives.BackendSampler>`.
            skip_transpilation: if :data:`True`, do not transpile circuits
              before passing them to the execution backend.

        Examples:
            Initialize a :class:`Sampler <qiskit.primitives.BaseSamplerV1>` primitive
            on a AQT offline simulator:

            >>> import qiskit
            >>> from qiskit_aqt_provider import AQTProvider
            >>> from qiskit_aqt_provider.primitives import AQTSampler
            >>>
            >>> backend = AQTProvider("").get_backend("offline_simulator_no_noise")
            >>> sampler = AQTSampler(backend)

            Configuring :class:`options <qiskit_aqt_provider.aqt_options.AQTOptions>`
            on the backend will affect all circuit evaluations triggered by
            the `Sampler` primitive:

            >>> qc = qiskit.QuantumCircuit(2)
            >>> _ = qc.cx(0, 1)
            >>> _ = qc.measure_all()
            >>>
            >>> sampler.run(qc).result().metadata[0]["shots"]
            100
            >>> backend.options.shots = 123
            >>> sampler.run(qc).result().metadata[0]["shots"]
            123

            The same effect is achieved by passing options to the
            :class:`AQTSampler` initializer:

            >>> sampler = AQTSampler(backend, options={"shots": 120})
            >>> sampler.run(qc).result().metadata[0]["shots"]
            120

            Passing the option in the
            :meth:`AQTSampler.run <qiskit.primitives.BaseSamplerV1.run>` call
            restricts the effect to a single evaluation:

            >>> sampler.run(qc, shots=130).result().metadata[0]["shots"]
            130
            >>> sampler.run(qc).result().metadata[0]["shots"]
            120
        """
        # Signal the transpiler to disable passes that require bound
        # parameters.
        # This allows the underlying sampler to apply most of
        # the transpilation passes, and cache the results.
        mod_backend = copy(backend)
        mod_backend._target = make_transpiler_target(
            transpiler_plugin.UnboundParametersTarget, backend.num_qubits
        )

        # if `with_progress_bar` is not explicitly set in the options, disable it
        options_copy = (options or {}).copy()
        options_copy.update(with_progress_bar=options_copy.get("with_progress_bar", False))

        super().__init__(
            mod_backend,
            bound_pass_manager=transpiler_plugin.bound_pass_manager(),
            options=options_copy,
            skip_transpilation=skip_transpilation,
        )

    @property
    def backend(self) -> AnyAQTResource:
        """Computing resource used for circuit evaluation."""
        return self._backend
