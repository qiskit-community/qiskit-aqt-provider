import json


def _experiment_to_seq(experiment):
    ops = []
    for inst in experiment.instructions:
        if inst.name == 'rx':
            name = 'X'
        elif inst.name == 'ry':
            name = 'Y'
        elif inst.name == 'rxx':
            name = 'MS'
        else:
            raise Exception('Gate outside of basis rx, ry, rxx')
        theta = inst['params'][0]
        # (op name, exponent, [qubit index])
        ops.append((name, theta, inst.qubits))
    return ops


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
            'no_qubits': qobj.config.n_qubits
        }
        out_json.append(json.dumps(out_dict))
    return out_json
