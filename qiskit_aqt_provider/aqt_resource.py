# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import sys
import warnings
from math import pi
from typing import Any, Dict, List, Union

import requests
from qiskit import QuantumCircuit, pulse
from qiskit import qobj as qobj_mod
from qiskit.circuit.library import RXGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.exceptions import QiskitError
from qiskit.providers import BackendV2 as Backend
from qiskit.providers import Options, Provider
from qiskit.providers.models import BackendConfiguration
from qiskit.transpiler import Target

from . import aqt_job_new
from .constants import REQUESTS_TIMEOUT

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class ApiResource(TypedDict):
    name: str
    id: str
    type: str  # Literal["simulator", "device"]


class AQTResource(Backend):
    def __init__(self, provider: Provider, workspace: str, resource: ApiResource):
        super().__init__(name="aqt_qasm_simulator", provider=provider)
        self._resource = resource
        self._workspace = workspace
        self.url = provider.portal_url
        self.headers = {
            "Authorization": f"Bearer {self._provider.access_token}",
            "SDK": "qiskit",
        }
        num_qubits = 20
        self._configuration = BackendConfiguration.from_dict(
            {
                "backend_name": resource["name"],
                "backend_version": 2,
                "url": self.url,
                "simulator": True,
                "local": False,
                "coupling_map": None,
                "description": "AQT trapped-ion device simulator",
                "basis_gates": ["r", "rz", "rxx"],  # the actual basis gates
                "memory": False,
                "n_qubits": num_qubits,
                "conditional": False,
                "max_shots": 200,
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [
                    {"name": "rz", "parameters": ["theta"], "qasm_def": "TODO"},
                    {"name": "r", "parameters": ["theta", "phi"], "qasm_def": "TODO"},
                    {"name": "rxx", "parameters": ["theta"], "qasm_def": "TODO"},
                ],
            }
        )
        self._target = Target(num_qubits=num_qubits)
        theta = Parameter("θ")
        lam = Parameter("λ")
        # configure the transpiler to use RX/RZ/RXX
        # the custom scheduling pass rewrites RX to R to comply to the Arnica API format.
        self._target.add_instruction(RZGate(lam))
        self._target.add_instruction(RXGate(theta))
        self._target.add_instruction(RXXGate(pi / 2.0))
        self._target.add_instruction(Measure())
        self.options.set_validator("shots", (1, 200))

    def submit(self, payload: Dict[str, Any]) -> str:
        """Submit a circuit.

        Parameters:
            payload: AQT Circuit API payload

        Returns:
            The unique identifier for the submitted job.
        """
        url = f"{self.url}/submit/{self._workspace}/{self._resource['id']}"
        req = requests.post(url, json=payload, headers=self.headers, timeout=REQUESTS_TIMEOUT)
        req.raise_for_status()
        response = req.json()

        api_job = response.get("job")
        if api_job is None:
            raise RuntimeError("API response does not contain field 'job'.")

        job_id = api_job.get("job_id")
        if job_id is None:
            raise RuntimeError("API response does not contain field 'job.job_id'.")

        return job_id

    def result(self, job_id: str) -> Dict[str, Any]:
        """Query the result for a specific job.

        Parameters:
            job_id: The unique identifier for the target job.

        Returns:
            Full returned payload.
        """
        url = f"{self.url}/result/{job_id}"
        req = requests.get(url, headers=self.headers, timeout=REQUESTS_TIMEOUT)
        req.raise_for_status()
        return req.json()

    def configuration(self):
        warnings.warn(
            (
                "The configuration() method is deprecated and will be removed in a "
                "future release. Instead you should access these attributes directly "
                "off the object or via the .target attribute. You can refer to qiskit "
                "backend interface transition guide for the exact changes: "
                "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2"
            ),
            DeprecationWarning,
        )
        return self._configuration

    def properties(self):
        warnings.warn(
            (
                "The properties() method is deprecated and will be removed in a "
                "future release. Instead you should access these attributes directly "
                "off the object or via the .target attribute. You can refer to qiskit "
                "backend interface transition guide for the exact changes: "
                "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2"
            ),
            DeprecationWarning,
        )

    @property
    def max_circuits(self):
        return 1

    @property
    def target(self):
        return self._target

    @classmethod
    def _default_options(cls):
        return Options(shots=100)

    def get_translation_stage_plugin(self) -> str:
        return "aqt"

    def get_scheduling_stage_plugin(self) -> str:
        return "aqt"

    def run(self, run_input: Union[QuantumCircuit, List[QuantumCircuit]], **options):
        if not isinstance(run_input, list):
            run_input = [run_input]

        if any(
            map(
                lambda x: isinstance(x, (qobj_mod.PulseQobj, pulse.Schedule, pulse.ScheduleBlock)),
                run_input,
            )
        ):
            raise QiskitError("Pulse jobs are not accepted")

        unknown_options = set(options) - set(self.options.__dict__ or {})
        if unknown_options:
            for unknown_option in unknown_options:
                warnings.warn(
                    f"Option {unknown_option} is not used by this backend",
                    UserWarning,
                    stacklevel=2,
                )

        # TODO: use the Options validator instead of custom logic here
        shots = options.get("shots", self.options.shots)

        if shots > self.configuration().max_shots:
            raise ValueError("Number of shots is larger than maximum number of shots")

        job = aqt_job_new.AQTJobNew(self, circuits=run_input, shots=shots)
        job.submit()
        return job
