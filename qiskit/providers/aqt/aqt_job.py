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

import time

import requests

from qiskit.providers import BaseJob
from qiskit.providers import JobError
from qiskit.providers import JobTimeoutError
from qiskit.result import Result
from .qobj_to_aqt import qobj_to_aqt


class AQTJob(BaseJob):
    def __init__(self, backend, job_id, access_token=None, qobj=None):
        super().__init__(backend, job_id)
        self._backend = backend
        self.access_token = access_token
        self.qobj = qobj
        self._job_id = job_id
        self.memory_mapping = self._build_memory_mapping()

    def _wait_for_result(self, timeout=None, wait=5):
        start_time = time.time()
        result = None
        header = {
            "Ocp-Apim-Subscription-Key": self._backend._provider.access_token,
            "SDK": "qiskit"
        }
        while True:
            elapsed = time.time() - start_time
            if timeout and elapsed >= timeout:
                raise JobTimeoutError('Timed out waiting for result')
            result = requests.put(
                self._backend.url,
                data={'id': self._job_id,
                      'access_token': self._backend._provider.access_token},
                headers=header
            ).json()
            if result['status'] == 'finished':
                break
            if result['status'] == 'error':
                raise JobError('API returned error:\n' + str(result))
            time.sleep(wait)
        return result

    def _build_memory_mapping(self):
        qu2cl = {}
        for instruction in self.qobj.experiments[0].instructions:
            if instruction.name == 'measure':
                qu2cl[instruction.qubits[0]] = instruction.memory[0]
        return qu2cl

    def _rearrange_result(self, input):
        length = self.qobj.experiments[0].header.memory_slots
        bin_output = list('0' * length)
        bin_input = list(bin(input)[2:].rjust(length, '0'))
        bin_input.reverse()
        for qu, cl in self.memory_mapping.items():
            bin_output[cl] = bin_input[qu]
        bin_output.reverse()
        return hex(int(''.join(bin_output), 2))

    def _format_counts(self, samples):
        counts = {}
        for result in samples:
            h_result = self._rearrange_result(result)
            if h_result not in counts:
                counts[h_result] = 1
            else:
                counts[h_result] += 1
        return counts

    def result(self):
        result = self._wait_for_result()
        results = [
            {
                'success': True,
                'shots': len(result['samples']),
                'data': {'counts': self._format_counts(result['samples'])},
                'header': {'memory_slots': self.qobj.config.memory_slots,
                           'name': self.qobj.experiments[0].header.name}
            }]

        return Result.from_dict({
            'results': results,
            'backend_name': self._backend._configuration.backend_name,
            'backend_version': self._backend._configuration.backend_version,
            'qobj_id': self.qobj.qobj_id,
            'success': True,
            'job_id': self._job_id,
        })

    def cancel(self):
        pass

    def status(self):
        header = {
            "Ocp-Apim-Subscription-Key": self._backend._provider.access_token,
            "SDK": "qiskit"
        }
        result = requests.put(self._backend.url,
                              data={'id': self._job_id,
                                    'access_token': self.access_token},
                              headers=header)
        return result['status']

    def submit(self):
        if not self.qobj or not self._job_id:
            raise Exception
        aqt_json = qobj_to_aqt(self.qobj, self.access_token)
        res = requests.post(self._backend.url, data=aqt_json[0])
        if 'id' not in res:
            raise Exception
        self._job_id = res['id']
