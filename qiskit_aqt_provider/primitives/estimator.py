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

from collections import defaultdict
from copy import copy
from typing import Any, Optional

import numpy as np
from qiskit import generate_preset_pass_manager
from qiskit.primitives import BackendEstimatorV2, PubResult
from qiskit.primitives.backend_estimator_v2 import (
    EstimatorPub,
    _prepare_counts,
    _PreprocessedData,
    _run_circuits,
)

from qiskit_aqt_provider.aqt_resource import AnyAQTResource, OfflineSimulatorResource


class AQTEstimator(BackendEstimatorV2):
    """:class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` primitive for AQT backends."""

    _backend: AnyAQTResource

    def __init__(
        self,
        *,
        backend: AnyAQTResource,
        options: Optional[dict[str, Any]] = None,
        auto_transpilation: bool = True,
        optimization_level: int = 0,
    ) -> None:
        """Initialize an ``Estimator`` primitive using an AQT backend.

        See :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` for
        examples configuring run options.

        Args:
            backend: AQT resource to evaluate circuits on.
            options: options passed to through to the underlying
              :class:`BackendEstimatorV2 <qiskit.primitives.BackendEstimatorV2>`.
            auto_transpilation: whether to automatically transpile circuits, defaults to True.
            optimization_level: the optimization level for transpilation, defaults to 0.
        """
        self.auto_transpilation = auto_transpilation
        self.optimization_level = optimization_level
        # disable progress bar
        backend.options.with_progress_bar = False
        # Set default precision in options so the amount of shots is the max amount possible
        options_copy = copy(options) if options is not None else {}
        if "default_precision" not in options_copy:
            # precision = 1/sqrt(shots), so shots = 1/precision^2
            # 0.022365 ≈ 1/sqrt(2000), resulting in ~2000 shots per circuit
            options_copy["default_precision"] = 0.022365

        super().__init__(
            backend=backend,
            options=options_copy,
        )

    @property
    def backend(self) -> AnyAQTResource:
        """Return the Estimator's backend."""
        return self._backend

    def _run_pubs(self, pubs: list[EstimatorPub], shots: int) -> list[PubResult]:
        """Compute results for pubs that all require the same value of ``shots``."""
        preprocessed_data = []
        flat_circuits = []
        for pub in pubs:
            data = self._preprocess_pub(pub)
            preprocessed_data.append(data)
            flat_circuits.extend(data.circuits)

        max_shots = type(self._backend.options).model_fields["shots"].metadata[1].le
        if max_shots and shots > max_shots:
            raise ValueError(
                f"Number of shots {shots} exceeds the backend's limit of {max_shots}. "
                "Consider reducing the precision of the estimation.",
            )

        if self._options.seed_simulator is None or not isinstance(
            self._backend, OfflineSimulatorResource
        ):
            run_result, metadata = _run_circuits(flat_circuits, self._backend, shots=shots)
        else:
            run_result, metadata = _run_circuits(
                flat_circuits,
                self._backend,
                shots=shots,
                seed_simulator=self._options.seed_simulator,
            )

        counts = _prepare_counts(run_result)

        results = []
        start = 0
        for pub, data in zip(pubs, preprocessed_data):
            end = start + len(data.circuits)
            expval_map = self._calc_expval_map(counts[start:end], metadata[start:end])
            start = end
            results.append(self._postprocess_pub(pub, expval_map, data, shots))

        return results

    def _preprocess_pub(self, pub: EstimatorPub) -> _PreprocessedData:
        """Converts a pub into a list of bound circuits necessary to estimate all its observables.

        The circuits contain metadata explaining which bindings array index they are with respect
        to, and which measurement basis they are measuring.

        Args:
            pub: The pub to preprocess.

        Returns:
            The values ``(circuits, bc_param_ind, bc_obs)`` where ``circuits`` are the circuits to
            execute on the backend, ``bc_param_ind`` are indices of the pub's bindings array and
            ``bc_obs`` is the observables array, both broadcast to the shape of the pub.
        """
        circuit = pub.circuit
        observables = pub.observables
        parameter_values = pub.parameter_values

        # calculate broadcasting of parameters and observables
        param_shape = parameter_values.shape
        param_indices = np.fromiter(np.ndindex(param_shape), dtype=object).reshape(param_shape)
        bc_param_ind, bc_obs = np.broadcast_arrays(param_indices, observables)

        param_obs_map: dict[Any, Any] = defaultdict(set)
        for index in np.ndindex(*bc_param_ind.shape):
            param_index = bc_param_ind[index]
            param_obs_map[param_index].update(bc_obs[index])

        bound_circuits = self._bind_and_add_measurements(circuit, parameter_values, param_obs_map)

        if self.auto_transpilation:
            pm = generate_preset_pass_manager(
                backend=self._backend, optimization_level=self.optimization_level
            )
            # don't use pass_manager.run(bound_circuits). It starts several processes and is slower
            final_circuits = [pm.run(qc) for qc in bound_circuits]
        else:
            final_circuits = bound_circuits

        return _PreprocessedData(final_circuits, bc_param_ind, bc_obs)
