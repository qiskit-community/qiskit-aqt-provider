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
# pylint: disable=protected-access

import unittest
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_backend import AQTDevice


class _FakeJob():
    def __init__(self, circuit):
        self.qobj = circuit

    def _build_memory_mapping(self):
        return AQTJob._build_memory_mapping(self)


class TestJobs(unittest.TestCase):

    def test_job_counts_measurement_mapping(self):
        """Are measurements correctly mapped to counts
        """
        perm = np.random.permutation(5)
        qc = QuantumCircuit(5, 5)
        qc.x(0)
        qc.x(2)
        qc.measure(range(5), perm)

        job = _FakeJob(qc)
        mapping = job._build_memory_mapping()

        self.assertEqual(mapping[0], perm[0])
        self.assertEqual(mapping[2], perm[2])

    def test_job_counts_measurement_mapping_with_circuit_list(self):
        """Are measurements correctly mapped to counts with circuit list"""
        perm = np.random.permutation(5)
        qc = QuantumCircuit(5, 5)
        qc.x(0)
        qc.x(2)
        qc.measure(range(5), perm)

        job = _FakeJob([qc])
        mapping = job._build_memory_mapping()

        self.assertEqual(mapping[0], perm[0])
        self.assertEqual(mapping[2], perm[2])

    def test_job_result_counts(self):
        qc = QuantumCircuit(2, 2)
        qc.x(range(2))
        qc.measure_all()
        backend = AQTDevice(None)
        tqc = transpile(qc, backend)
        job = AQTJob(backend, 'abc123', None, tqc)
        fake_response = {
            'id': 'abc123',
            'no_qubits': 2,
            'received': [['X', 0.5, [0]],
                         ['X', 0.5, [0]],
                         ['X', 0.5, [1]],
                         ['X', 0.5, [1]]],
            'repetitions': 200,
            'samples': [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                        3, 3],
            'status': 'finished'
        }
        with unittest.mock.patch.object(job, '_wait_for_result',
                                        return_value=fake_response):
            result = job.result()

        self.assertEqual({'1100': 198, '1000': 1, '0100': 1},
                         result.get_counts())
