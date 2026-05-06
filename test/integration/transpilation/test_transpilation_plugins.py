from math import pi

import pytest
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.transpiler import StagedPassManager, generate_preset_pass_manager

from test.helpers import assert_circuits_equivalent
from test.integration.helpers import get_dummy_cloud_resource


def collect_pass_names(passmanager: StagedPassManager) -> list[str]:
    """Helper function to collect the names of passes in a pass manager."""
    names: list[str] = []
    for tasklist in passmanager._tasks:
        for task in tasklist:
            names.append(type(task).__name__)  # noqa: PERF401
    return names


def test_translation_plugins_are_registered_with_cloud_backends() -> None:
    """The appropriate AQT transpiler plugins for translation and scheduling should be registered with AQT backends.

    They should be used during transpilation for those backends. This test checks that the expected passes from the
    plugins are present in the preset pass manager for a CloudResource.
    """
    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource())

    translation_passes = set(collect_pass_names(pm.translation))
    scheduling_passes = set(collect_pass_names(pm.scheduling))

    assert "WrapRxxAngles" in translation_passes
    assert scheduling_passes == {
        "EnsureSingleFinalMeasurement",
        "Decompose",
        "RewriteRxAsR",
        "WrapRxxAngles",
        "Optimize1qGatesDecomposition",
    }


@pytest.mark.parametrize(("optimization_level"), [0, 1, 2, 3])
def test_transpile_and_generate_preset_pass_manager_run_produce_the_same_results(optimization_level: int) -> None:
    """Transpiling a circuit with the preset pass manager for an AQT cloud resource should produce the same result as
    using the transpile function with that resource as the backend.
    """
    qc = QuantumCircuit(2)
    qc.h(1)
    qc.ry(0.5, 0)
    qc.rxx(12, 0, 1)
    qc.h(0)
    qc.measure_all()
    backend = get_dummy_cloud_resource()

    transpiled_1 = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level).run(qc)
    transpiled_2 = transpile(backend=backend, circuits=qc, optimization_level=optimization_level)

    assert transpiled_1 == transpiled_2


def test_transpilation_plugin_passes_order() -> None:
    """The order of passes in the translation plugins should be correct."""
    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource(), optimization_level=0)

    translation_passes = collect_pass_names(pm.translation)
    scheduling_passes = collect_pass_names(pm.scheduling)

    assert translation_passes[-2:] == ["WrapRxxAngles", "Decompose"]
    assert scheduling_passes[-5:] == [
        "WrapRxxAngles",
        "Decompose",
        "Optimize1qGatesDecomposition",
        "RewriteRxAsR",
        "EnsureSingleFinalMeasurement",
    ]


@pytest.mark.parametrize(("optimization_level"), [0, 1, 2, 3])
def test_transpilation_passes_respect_optimization_levels(optimization_level: int) -> None:
    """The optimization level should be taken into account when generating the pass manager."""
    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource(), optimization_level=optimization_level)

    translation_passes = collect_pass_names(pm.translation)

    if optimization_level == 0:
        assert translation_passes[-2:] == ["WrapRxxAngles", "Decompose"]
    else:
        assert translation_passes[-1] == "WrapRxxAngles"


def test_decompose_1q_rotations_example() -> None:
    """Snapshot test for the efficient rewrite of single-qubit rotation runs as ZXZ."""
    qc = QuantumCircuit(1)
    qc.rx(pi / 2, 0)
    qc.ry(pi / 2, 0)
    expected = QuantumCircuit(1)
    expected.rz(-pi / 2, 0)
    expected.r(pi / 2, 0, 0)

    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource(), optimization_level=3)
    result = pm.run(qc)

    assert isinstance(result, QuantumCircuit)
    assert_circuits_equivalent(result, expected)
    assert result == expected
