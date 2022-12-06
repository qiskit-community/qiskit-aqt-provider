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

from math import pi
import sys

import warnings

import requests

from qiskit import qobj as qobj_mod
from qiskit.circuit.parameter import Parameter
from qiskit.circuit.library import RZGate, RGate, RXXGate
from qiskit.circuit.measure import Measure
from qiskit.providers import BackendV2 as Backend
from qiskit.providers import Options
from qiskit.transpiler import Target
from qiskit.providers.models import BackendConfiguration
from qiskit.exceptions import QiskitError

from . import aqt_job_new
from . import circuit_to_aqt

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class ApiResource(TypedDict):
    name: str
    id: str
    type: str  # Literal["simulator", "device"]


class AQTResource(Backend):

    def __init__(self, provider, workspace: str, resource: ApiResource):
        super().__init__(
            name="aqt_qasm_simulator",
            provider=provider)
        self._resource = resource
        self._workspace = workspace
        self.url = provider.portal_url
        self.headers = {"Authorization": f"Bearer {self._provider.access_token}", "SDK": "qiskit"}
        num_qubits = 20
        self._configuration = BackendConfiguration.from_dict({
            'backend_name': resource["name"],
            'backend_version': '0.0.1',
            'url': self.url,
            'simulator': True,
            'local': False,
            'coupling_map': None,
            'description': 'AQT trapped-ion device simulator',
            'basis_gates': ['rz', 'r', 'rxx'],
            'memory': False,
            'n_qubits': num_qubits,
            'conditional': False,
            'max_shots': 200,
            'max_experiments': 1,
            'open_pulse': False,
            'gates': [
                {
                    'name': 'TODO',
                    'parameters': [],
                    'qasm_def': 'TODO'
                }
            ]
        })
        self._target = Target(num_qubits=num_qubits)
        theta = Parameter('θ')
        phi = Parameter('ϕ')
        lam = Parameter('λ')
        self._target.add_instruction(RZGate(lam))
        self._target.add_instruction(RGate(theta, phi))
        self._target.add_instruction(RXXGate(pi/2.0))
        self._target.add_instruction(Measure())
        self.options.set_validator("shots", (1, 200))

    def configuration(self):
        warnings.warn("The configuration() method is deprecated and will be removed in a "
                      "future release. Instead you should access these attributes directly "
                      "off the object or via the .target attribute. You can refer to qiskit "
                      "backend interface transition guide for the exact changes: "
                      "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2",
                      DeprecationWarning)
        return self._configuration

    def properties(self):
        warnings.warn("The properties() method is deprecated and will be removed in a "
                      "future release. Instead you should access these attributes directly "
                      "off the object or via the .target attribute. You can refer to qiskit "
                      "backend interface transition guide for the exact changes: "
                      "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2",
                      DeprecationWarning)

    @property
    def max_circuits(self):
        return 1

    @property
    def target(self):
        return self._target

    @classmethod
    def _default_options(cls):
        return Options(shots=100)

    def run(self, run_input, **options):
        if isinstance(run_input, qobj_mod.PulseQobj):
            raise QiskitError("Pulse jobs are not accepted")
        for option in options:
            if option != 'shots':
                warnings.warn(
                    f"Option {option} is not used by this backend",
                    UserWarning, stacklevel=2)
        out_shots = options.get('shots', self.options.shots)
        if out_shots > self.configuration().max_shots:
            raise ValueError('Number of shots is larger than maximum '
                             'number of shots')
        aqt_json = circuit_to_aqt.circuit_to_aqt_new(
            run_input, shots=out_shots)

        # print(aqt_json)
        res = requests.post(
            f"{self.url}/submit/{self._workspace}/{self._resource['id']}",
            json=aqt_json,
            headers=self.headers,
        )
        res.raise_for_status()
        response = res.json()
        api_job = response.get("job")
        if api_job is None:
            raise Exception("API Response does not contain field 'job'.")
        job_id = api_job.get("job_id")
        if job_id is None:
            raise Exception("API Response does not contain field 'job'.'job_id'.")
        print(job_id)
        job = aqt_job_new.AQTJobNew(self, job_id, qobj=run_input)
        return job
