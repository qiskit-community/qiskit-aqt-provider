# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import json

from numpy import pi


def _experiment_to_seq(experiment):
    ops = []
    meas = 0
    for inst in experiment.instructions:
        if inst.name == 'rx':
            name = 'X'
        elif inst.name == 'ry':
            name = 'Y'
        elif inst.name == 'rxx':
            name = 'MS'
        elif inst.name == 'ms':
            name = 'MS'
            inst.qubits = []
        elif inst.name == 'measure':
            meas += 1
            continue
        elif inst.name == 'barrier':
            continue
        else:
            raise Exception("Operation '%s' outside of basis rx, ry, rxx" %
                            inst.name)
        exponent = inst.params[0] / pi

        # hack: split X into X**0.5 . X**0.5
        if name == 'X' and exponent == 1.0:
            ops.append((name, float(0.5), inst.qubits))
            ops.append((name, float(0.5), inst.qubits))
        else:
            # (op name, exponent, [qubit index])
            ops.append((name, float(exponent), inst.qubits))
    if not meas:
        raise ValueError('Circuit must have at least one measurements.')
    return json.dumps(ops)


def qobj_to_aqt(qobj, access_token):
    """Return a list of json payload strings for each experiment in a qobj

    The output json format of an experiment is defined as follows:
        [[op_string, gate_exponent, qubits]]

    which is a list of sequential quantum operations, each operation defined
    by:

    op_string: str that specifies the operation type, either "X","Y","MS"
    gate_exponent: float that specifies the gate_exponent of the operation
    qubits: list of qubits where the operation acts on.
    """
    out_json = []
    if len(qobj.experiments) > 1:
        raise Exception
    for experiment in qobj.experiments:
        seqs = _experiment_to_seq(experiment)
        out_dict = {
            'data': seqs,
            'access_token': access_token,
            'repetitions': qobj.config.shots,
            'no_qubits': qobj.config.n_qubits,
        }
        out_json.append(out_dict)
    return out_json
