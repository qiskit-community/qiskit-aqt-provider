# (C) Copyright Alpine Quantum Technologies GmbH 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Experimental QIR to AQT API conversion routines."""

import dataclasses
import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Union

import pyqir

from qiskit_aqt_provider import api_models


def qir_to_aqt_circuit(module: pyqir.Module) -> api_models.Circuit:
    """Convert a QIR module representing a quantum circuit to an equivalent AQT API payload.

    Args:
        module: QIR module to convert.

    Returns:
        AQT API payload that corresponds to the first entry point found in the QIR module.

    Limitations:
        - only the first entry point found is converted. Other entry points are ignored.
        - only the following gates are supported: RX, RY, RZ, X, Y, Z, RXX.
        - no classical code is allowed (including non QIS function calls).
        - except for the initialization routine, no quantum runtime operations are allowed.
        - measurements are bunched at the end of the circuit.
        - in the QIR logic, qubits targeted by a measurement cannot be operated on after the measurement.
    """
    if (error_msg := module.verify()) is not None:  # pragma: no cover
        msg = f"Invalid LLVM module: {error_msg}"
        raise ValueError(msg)

    # TODO?: support multiple entry points (one circuit per entry point)
    entry_points = [func for func in module.functions if pyqir.is_entry_point(func)]
    if not entry_points:
        msg = "No entry point found."
        raise ValueError(msg)

    ctx = _Context()
    ops = list(_traverse_function(entry_points[0], ctx))

    if not ctx.measured_qubits:
        msg = "No measurement operation found."
        raise ValueError(msg)

    ops.append(api_models.Operation.measure())

    return api_models.Circuit(root=ops)


def load_llvm_module(data: Union[str, bytes]) -> pyqir.Module:
    """Load a QIR module, from LLVM bitcode or human-readable representation.

    Args:
        data: QIR module to load. If a string, assume human-readable format, else
          LLVM bitcode.
    """
    ctx = pyqir.Context()

    if isinstance(data, str):
        return pyqir.Module.from_ir(ctx, data)

    return pyqir.Module.from_bitcode(ctx, data)


@dataclass
class _Context:
    """Context for AQT JSON emission."""

    measured_qubits: set[int] = dataclasses.field(default_factory=set)


def _traverse_function(
    func: pyqir.Function, context: _Context
) -> Iterator[api_models.OperationModel]:
    """Traverse a function definition and emit AQT API operations for the found QIS calls."""
    for bb in func.basic_blocks:
        for inst in bb.instructions:
            if isinstance(inst, pyqir.Call):
                yield from _convert_call(inst, context)
            elif inst.opcode == pyqir.Opcode.RET:
                break
            else:
                msg = f"Unsupported instruction: {inst}"
                raise ValueError(msg)


# C901 (complexity too high): complexity is high but structure mostly flat due to instructions dispatch.
def _convert_call(inst: pyqir.Call, context: _Context) -> Iterator[api_models.OperationModel]:  # noqa: C901
    """Emit AQT API operations for a given QIR call instruction."""
    func_name = inst.callee.name

    def ensure_can_operate_on_qubit(qubit: int) -> int:
        if qubit in context.measured_qubits:
            msg = f"Cannot operate on {qubit=}: was already measured."
            raise ValueError(msg)

        return qubit

    if func_name == "__quantum__rt__initialize":
        return  # ignore, no-op
    elif func_name == "__quantum__qis__rx__body":
        angle_arg, qubit_arg = inst.args
        assert isinstance(angle_arg, pyqir.FloatConstant)  # noqa: S101
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101
        angle = angle_arg.value

        theta = math.atan2(math.sin(angle), math.cos(angle))
        phi = math.pi if theta < 0.0 else 0.0

        yield api_models.Operation.r(
            phi=phi / math.pi,
            theta=abs(theta) / math.pi,
            qubit=ensure_can_operate_on_qubit(_extract_qubit_id(qubit_arg)),
        )
    elif func_name == "__quantum__qis__x__body":
        (qubit_arg,) = inst.args
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101

        yield api_models.Operation.r(
            phi=0.0,
            theta=1.0,
            qubit=ensure_can_operate_on_qubit(_extract_qubit_id(qubit_arg)),
        )
    elif func_name == "__quantum__qis__ry__body":
        angle_arg, qubit_arg = inst.args
        assert isinstance(angle_arg, pyqir.FloatConstant)  # noqa: S101
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101
        angle = angle_arg.value

        theta = math.atan2(math.sin(angle), math.cos(angle))
        phi = math.pi / 2 + (math.pi if theta < 0.0 else 0.0)

        yield api_models.Operation.r(
            phi=phi / math.pi,
            theta=abs(theta) / math.pi,
            qubit=ensure_can_operate_on_qubit(_extract_qubit_id(qubit_arg)),
        )
    elif func_name == "__quantum__qis__y__body":
        (qubit_arg,) = inst.args
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101

        yield api_models.Operation.r(
            phi=0.5,
            theta=1.0,
            qubit=ensure_can_operate_on_qubit(_extract_qubit_id(qubit_arg)),
        )
    elif func_name == "__quantum__qis__rz__body":
        angle_arg, qubit_arg = inst.args
        assert isinstance(angle_arg, pyqir.FloatConstant)  # noqa: S101
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101
        angle = angle_arg.value

        phi = math.atan2(math.sin(angle), math.cos(angle))

        yield api_models.Operation.rz(
            phi=phi / math.pi,
            qubit=ensure_can_operate_on_qubit(_extract_qubit_id(qubit_arg)),
        )
    elif func_name == "__quantum__qis__z__body":
        (qubit_arg,) = inst.args
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101

        yield api_models.Operation.rz(
            phi=1.0,
            qubit=_extract_qubit_id(qubit_arg),
        )
    # no cover: missing tooling support for emitting / manipulating RXX gates
    # in pyqir/qiskit_qir.
    elif func_name == "__quantum__qis__rxx__body":  # pragma: no cover
        angle_arg, qubit0_arg, qubit1_arg = inst.args
        assert isinstance(angle_arg, pyqir.FloatConstant)  # noqa: S101
        assert isinstance(qubit0_arg, pyqir.Constant)  # noqa: S101
        assert isinstance(qubit1_arg, pyqir.Constant)  # noqa: S101
        angle = angle_arg.value

        if angle < 0 or angle > math.pi / 2:
            msg = "__quantum__qis__rxx__body angle must be in [0, π/2]."
            raise ValueError(msg)

        yield api_models.Operation.rxx(
            theta=angle / math.pi,
            qubits=[
                ensure_can_operate_on_qubit(_extract_qubit_id(qubit0_arg)),
                ensure_can_operate_on_qubit(_extract_qubit_id(qubit1_arg)),
            ],
        )
    elif func_name == "__quantum__qis__mz__body":
        qubit_arg, _ = inst.args
        assert isinstance(qubit_arg, pyqir.Constant)  # noqa: S101

        context.measured_qubits.add(_extract_qubit_id(qubit_arg))
    else:
        # TODO: support local functions
        msg = f"Unsupported function: {func_name}"
        raise ValueError(msg)


def _extract_qubit_id(value: pyqir.Constant) -> int:
    """Extract a Qubit identifier from a LLVM constant.

    Raises:
        ValueError: no identifier could be extracted.
    """
    if (qubit_id := pyqir.qubit_id(value)) is None:  # pragma: no cover
        msg = "Invalid Qubit struct pointer."
        raise ValueError(msg)

    return qubit_id
