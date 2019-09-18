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

    def test_empty_circuit_qobj(self):
        qobj = assemble(QuantumCircuit(1))
        aqt_json = qobj_to_aqt(qobj, 'foo')
        self.assertEqual(
            ['{"data": [], "access_token": "foo", "repetitions": 1024, '
             '"no_qubits": 1}'], aqt_json)

    def test_invalid_basis_in_qobj(self):
        qc = QuantumCircuit(1)
        qc.h(0)
        qobj = assemble(qc)
        self.assertRaises(Exception, qobj_to_aqt, qobj, 'foo')

    def test_with_single_rx(self):
        qc = QuantumCircuit(1)
        qc.rx(pi, 0)
        qobj = assemble(qc)
        expected = [
            '{"data": [["X", "1.000000", [0]]], "access_token": "foo", '
            '"repetitions": 1024, "no_qubits": 1}']
        self.assertEqual(expected, qobj_to_aqt(qobj, 'foo'))

    def test_with_single_rx(self):
        qc = QuantumCircuit(1)
        qc.ry(pi, 0)
        qobj = assemble(qc)
        expected = [
            '{"data": [["Y", "1.000000", [0]]], "access_token": "foo", '
            '"repetitions": 1024, "no_qubits": 1}']
        self.assertEqual(expected, qobj_to_aqt(qobj, 'foo'))
