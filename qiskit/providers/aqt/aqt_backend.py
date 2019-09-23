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

import requests

from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration
from . import aqt_job
from . import qobj_to_aqt


class AQTBackend(BaseBackend):

    def __init__(self, provider):
        configuration = {
            'backend_name': 'aqt_innsbruck',
            'backend_version': '0.0.1',
            'url': getattr(provider, '_url', 'https://www.aqt.eu/'),
            'simulator': False,
            'local': False,
            'coupling_map': [[0, 1], [0, 2], [0, 3], [0, 4],
                             [1, 0], [1, 2], [1, 3], [1, 4],
                             [2, 0], [2, 1], [2, 3], [2, 4],
                             [3, 0], [3, 1], [3, 2], [3, 4],
                             [4, 0], [4, 1], [4, 2], [4, 3]],
            'description': 'aqt trapped ion device',
            'basis_gates': ['rx', 'ry', 'rxx'],
            'memory': False,
            'n_qubits': 5,
            'conditional': False,
            'max_shots': 250,
            'open_pulse': False,
            'gates': [
                {
                    'name': 'TODO',
                    'parameters': [],
                    'qasm_def': 'TODO'
                }
            ]
        }

        # We will explain about the provider in the next section
        super().__init__(
            configuration=BackendConfiguration.from_dict(configuration),
            provider=provider)

    def run(self, qobj):
        aqt_json = qobj_to_aqt.qobj_to_aqt(
            qobj, self._provider.access_token)[0]
        res = requests.put(self._provider.url, data=aqt_json)
        res.raise_for_status()
        response = res.json()
        if 'id' not in response:
            raise Exception
        job = aqt_job.AQTJob(self, response['id'], qobj=qobj)
        return job
