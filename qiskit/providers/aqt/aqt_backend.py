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
from qiskit.providers.aqt import aqt_job
from qiskit.providers.aqt import qobj_to_aqt


class AQTBackend(BaseBackend):

    def __init__(self, provider=None):
        configuration = {
            'backend_name': 'aqt',
            'backend_version': '0.0.1',
            'url': 'https://www.aqt.eu/',
            'simulator': False,
            'local': False,
            'coupling_map': None,
            'description': 'aqt trapped ion device',
            'basis_gates': ['rx', 'ry', 'rxx'],
            'memory': True,
            'n_qubits': 5,
            'conditional': False,
            'max_shots': 1024,
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
        aqt_json = qobj_to_aqt.qobj_to_aqt(qobj, self.access_token)
        res = requests.post(self.configuration.url, data=aqt_json[0])
        if 'id' not in res:
            raise Exception
        job = aqt_job.AQTJob(self, res['id'])
        return job
