from copy import copy
from typing import Any, Optional

import numpy as np
from qiskit.primitives import (
    BackendSamplerV2,
    SamplerPubResult,
)
from qiskit.primitives.backend_estimator_v2 import _run_circuits
from qiskit.primitives.backend_sampler_v2 import _analyze_circuit, _prepare_memory
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_aqt_provider.aqt_resource import AnyAQTResource


class AQTSampler(BackendSamplerV2):
    """Class for interacting with the AQT provider's Sampler service.

    As circuit transpilation for AQT backends includes angle wrapping, the transpilation needs to be done after
    parameter binding. In order for the AQTSampler to support parameterized circuits, it needs to transpile circuits
    when it is run.

    For use cases where full control over transpilation is required and no parameterized circuits are used, the
    transpilation by the sampler can be skipped with the :attr:`skip_transpilation` parameter and backend-compatible
    circuits provided to the sampler.

    Providing options to the :class:`AQTSampler` on instantiation will affect all circuit evaluations.
    Setting :class:`options <qiskit_aqt_provider.aqt_options.AQTOptions>` on the backend has the same effect.
    Passing options in :meth:`AQTSampler.run <qiskit.primitives.BaseSamplerV2.run>` restricts the effect to that
    evaluation.
    """

    _backend: AnyAQTResource

    def __init__(
        self,
        backend: AnyAQTResource,
        *,
        options: Optional[dict[str, Any]] = None,
        skip_transpilation: bool = False,
        optimization_level: int = 0,
    ) -> None:
        """Initialize a ``Sampler`` primitive using an AQT backend.

        Args:
            backend: AQT resource to evaluate circuits on.
            options: options passed through to the underlying
              :class:`BackendSamplerV2 <qiskit.primitives.BackendSamplerV2>`.
            skip_transpilation: if :data:`True`, do not transpile circuits
              before passing them to the execution backend, defaults to :data:`False`.
            optimization_level: the optimization level for transpilation, defaults to 0.
        """
        self.skip_transpilation = skip_transpilation
        self.optimization_level = optimization_level
        # disable progress bar
        backend.options.with_progress_bar = False
        # Set default shots in options
        options_copy = copy(options) if options is not None else {}
        if "default_shots" not in options_copy:
            options_copy["default_shots"] = backend.options.shots

        super().__init__(
            backend=backend,
            options=options_copy,
        )

    @property
    def backend(self) -> AnyAQTResource:
        """Return the Sampler's backend."""
        return self._backend

    def _run_pubs(self, pubs: list[SamplerPub], shots: int) -> list[SamplerPubResult]:
        """Compute results for pubs that all require the same value of ``shots``.

        Overrides the parent :class:`BaseSamplerV2 <qiskit.primitives.BaseSamplerV2>` function
        :meth: `_run_pubs` to add functionality for:
        - Checking if the maximum amount of shots the backend is capable of, is not exceeded.
        - Transpile circuits after parameters were bound.
        - Convert memory to hex strings for postprocessing with :meth:`_postprocess_pub`.
        """
        max_shots = type(self._backend.options).model_fields["shots"].metadata[1].le
        if max_shots and shots > max_shots:
            raise ValueError(f"Number of shots {shots} exceeds the backend's limit of {max_shots}.")

        # prepare circuits
        bound_circuits = [pub.parameter_values.bind_all(pub.circuit) for pub in pubs]
        flatten_circuits = []
        for bc in bound_circuits:
            flatten_circuits.extend(np.ravel(bc).tolist())

        if not self.skip_transpilation:
            pm = generate_preset_pass_manager(backend=self._backend, optimization_level=self.optimization_level)
            # don't use pass_manager.run(bound_circuits). It starts several processes and is slower
            circuits = [pm.run(qc) for qc in flatten_circuits]
        else:
            circuits = flatten_circuits

        run_opts = self._options.run_options or {}
        # run circuits
        results, _ = _run_circuits(
            circuits,
            self._backend,
            clear_metadata=False,
            memory=True,
            shots=shots,
            seed_simulator=self._options.seed_simulator,
            **run_opts,
        )
        result_memory = _prepare_memory(results)

        # convert memory to hex strings to be postprocessed into counts by _postprocess_pub
        result_memory_hex = [[hex(int(str(i), 2)) for i in m] for m in result_memory]

        # pack memory to an ndarray of uint8
        results = []
        start = 0
        meas_level = run_opts.get("meas_level")
        for pub, bound in zip(pubs, bound_circuits):
            meas_info, max_num_bytes = _analyze_circuit(pub.circuit)
            end = start + bound.size
            results.append(
                self._postprocess_pub(
                    result_memory_hex[start:end],
                    shots,
                    bound.shape,
                    meas_info,
                    max_num_bytes,
                    pub.circuit.metadata,
                    meas_level,
                )
            )
            start = end

        return results
