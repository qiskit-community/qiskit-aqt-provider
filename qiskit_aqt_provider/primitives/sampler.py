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

import numpy as np
from qiskit.primitives import (
    BackendSamplerV2,
    SamplerPubResult,
)
from qiskit.primitives.backend_sampler_v2 import _analyze_circuit, _prepare_memory
from qiskit.primitives.containers.sampler_pub import SamplerPub
from qiskit.transpiler import generate_preset_pass_manager

from qiskit_aqt_provider.aqt_resource import AnyAQTResource
from qiskit_aqt_provider.primitives.estimator import _run_circuits


class AQTSampler(BackendSamplerV2):
    """Class for interacting with the AQT provider's Sampler service."""

    _backend: AnyAQTResource

    def __init__(
        self,
        backend: AnyAQTResource,
        *,
        options: Optional[dict[str, Any]] = None,
        auto_transpilation: bool = True,
        optimization_level: int = 0,
    ) -> None:
        """Initialize a ``Sampler`` primitive using an AQT backend.

        Args:
            backend: AQT resource to evaluate circuits on.
            options: options passed through to the underlying
              :class:`BackendSamplerV2 <qiskit.primitives.BackendSamplerV2>`.
            auto_transpilation: whether to automatically transpile circuits, defaults to True.
            optimization_level: the optimization level for transpilation, defaults to 0.
        """
        self.auto_transpilation = auto_transpilation
        self.optimization_level = optimization_level
        # Signal the transpiler to disable passes that require bound
        # parameters.
        # This allows the underlying sampler to apply most of
        # the transpilation passes, and cache the results.

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
        """Compute results for pubs that all require the same value of ``shots``."""
        # prepare circuits
        bound_circuits = [pub.parameter_values.bind_all(pub.circuit) for pub in pubs]
        flatten_circuits = []
        for bc in bound_circuits:
            flatten_circuits.extend(np.ravel(bc).tolist())

        if self.auto_transpilation:
            pm = generate_preset_pass_manager(
                backend=self._backend, optimization_level=self.optimization_level
            )
            circuits = pm.run(flatten_circuits)
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
