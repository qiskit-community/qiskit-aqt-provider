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

import unittest

from numpy import pi
from qiskit import QuantumCircuit
from qiskit.compiler import assemble

from qiskit.providers.aqt.qobj_to_aqt import qobj_to_aqt


class TestQobjToAQT(unittest.TestCase):

    def test_empty_circuit(self):
        qc = QuantumCircuit(1)
        qobj = assemble(qc)
        self.assertRaises(ValueError, qobj_to_aqt, qobj, 'foo')

    def test_just_measure_circuit_qobj(self):
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        qobj = assemble(qc)
        aqt_json = qobj_to_aqt(qobj, 'foo')
        self.assertEqual(
            [{'access_token': 'foo', 'data': '[]', 'no_qubits': 1,
              'repetitions': 1024}], aqt_json)

    def test_invalid_basis_in_qobj(self):
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        qobj = assemble(qc)
        self.assertRaises(Exception, qobj_to_aqt, qobj, 'foo')

    def test_with_single_rx(self):
        qc = QuantumCircuit(1, 1)
        qc.rx(pi, 0)
        qc.measure(0, 0)
        qobj = assemble(qc)
        expected = [{'access_token': 'foo',
                     'data': '[["X", 0.5, [0]], ["X", 0.5, [0]]]',
                     'no_qubits': 1,
                     'repetitions': 1024}]
        self.assertEqual(expected, qobj_to_aqt(qobj, 'foo'))

    def test_with_two_rx(self):
        qc = QuantumCircuit(1, 1)
        qc.rx(pi, 0)
        qc.rx(2*pi, 0)
        qc.measure(0, 0)
        qobj = assemble(qc)
        expected = [{'access_token': 'foo',
                     'data': '[["X", 0.5, [0]], ["X", 0.5, [0]], '
                             '["X", 2.0, [0]]]',
                     'no_qubits': 1,
                     'repetitions': 1024}]
        self.assertEqual(expected, qobj_to_aqt(qobj, 'foo'))

    def test_with_single_ry(self):
        qc = QuantumCircuit(1, 1)
        qc.ry(pi, 0)
        qc.measure(0, 0)
        qobj = assemble(qc)
        expected = [{'access_token': 'foo',
                     'data': '[["Y", 1.0, [0]]]',
                     'no_qubits': 1,
                     'repetitions': 1024}]
        self.assertEqual(expected, qobj_to_aqt(qobj, 'foo'))
