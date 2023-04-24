# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import importlib.metadata
from math import pi
from typing import Callable

import pytest
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives import BackendSampler, BaseSampler, Sampler
from qiskit.providers import Backend
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_aqt_provider.aqt_resource import AQTResource


@pytest.mark.skipif(
    importlib.metadata.version("qiskit-terra") >= "0.24.0",
    reason="qiskit.opflow is deprecated in qiskit-terra>=0.24",
)
def test_circuit_sampling_opflow(offline_simulator_no_noise: AQTResource) -> None:
    """Check that an `AQTResource` can be used as backend for the legacy
    `opflow.CircuitSampler` with parametric circuits.
    """
    from qiskit.opflow import CircuitSampler, StateFn

    theta = Parameter("θ")

    qc = QuantumCircuit(2)
    qc.rx(theta, 0)
    qc.ry(theta, 0)
    qc.rz(theta, 0)
    qc.rxx(theta, 0, 1)

    assert qc.num_parameters > 0

    sampler = CircuitSampler(offline_simulator_no_noise)

    sampled = sampler.convert(StateFn(qc), params={theta: pi}).eval()
    assert sampled.to_matrix().tolist() == [[0.0, 0.0, 0.0, 1.0]]


@pytest.mark.parametrize(
    "get_sampler",
    [
        lambda _: Sampler(),
        # The AQT transpilation plugin doesn't support transpiling unbound parametric circuits
        # and the BackendSampler doesn't fallback to transpiling the bound circuit if
        # transpiling the unbound circuit failed (like the opflow sampler does).
        # Sampling a parametric circuit with an AQT backend is therefore not supported.
        pytest.param(
            lambda backend: BackendSampler(backend), marks=pytest.mark.xfail(raises=TranspilerError)
        ),
    ],
)
def test_circuit_sampling_primitive(
    get_sampler: Callable[[Backend], BaseSampler],
    offline_simulator_no_noise: AQTResource,
) -> None:
    """Check that a `Sampler` primitive using an AQT backend can sample parametric circuits."""
    theta = Parameter("θ")

    qc = QuantumCircuit(2)
    qc.rx(theta, 0)
    qc.ry(theta, 0)
    qc.rz(theta, 0)
    qc.rxx(theta, 0, 1)
    qc.measure_all()

    assert qc.num_parameters > 0

    sampler = get_sampler(offline_simulator_no_noise)
    sampled = sampler.run(qc, [pi]).result().quasi_dists
    assert sampled == [{3: 1.0}]
