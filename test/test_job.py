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
from qiskit import QuantumCircuit
from qiskit.providers.aqt import AQT
from qiskit.providers.aqt.aqt_job import AQTJob


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
        qc = QuantumCircuit(5,5)
        qc.x(0)
        qc.x(2)
        qc.measure(range(5), perm)

        job = _FakeJob(qc)
        mapping = job._build_memory_mapping()

        self.assertEqual(mapping[0], perm[0])
        self.assertEqual(mapping[2], perm[2])
