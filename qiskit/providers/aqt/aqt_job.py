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


import time

from qiskit.providers import BaseJob
from qiskit.providers import JobError
from qiskit.providers import JobTimeoutError
from qiskit.result import Result
import requests

from qiskit_aqt import qobj_to_aqt


class AQTJob(BaseJob):
    def __init__(self, backend, job_id, access_token=None, qobj=None):
        super().__init__(backend, job_id)
        self._backend = backend
        self.access_token = access_token
        self.qobj = qobj

    def _wait_for_result(self, timeout=None, wait=5):
        start_time = time.time()
        result = None
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise JobTimeoutError('Timed out waiting for result')
            result = requests.put(self._backend.url,
                                  data={'id': self._job_id,
                                        'access_token': self.access_token})
            if result['status'] == 'finished':
                break
            elif result['status'] == 'error':
                raise JobError('API returned error:\n' + str(result))
            time.sleep(wait)
        return result

    def _format_counts(samples):
        counts = {}
        for result in samples:
            if hex(result) not in counts:
                counts[hex(result)] = 1
            else:
                counts[hex(result)] = counts[hex(result)] + 1
        return counts

    def result(self):
        result = self._wait_for_result()
        results = [
            {
                'name': '',
                'success': True,
                'shots': len(result['samples']),
                'data': {'counts': self._format_counts(result['samples'])},
            }]
        return Result.from_dict({
            'results': results,
            'backend_name': self._backend.name,
            'backend_version': self._backend.version,
            'qobj_id': '0',
            'job_id': self._job_id,
        })

    def cancel(self):
        pass

    def status(self):
        result = requests.put(self._backend.url,
                              data={'id': self._job_id,
                                    'access_token': self.access_token})
        return result['status']

    def submit(self):
        if not self.qobj or not self._job_id:
            raise Exception
        aqt_json = qobj_to_aqt(self.qobj)
        res = requests.post(self.configuration.url, data=aqt_json[0])
        if 'id' not in res:
            raise Exception
        self._job_id = res['id']
