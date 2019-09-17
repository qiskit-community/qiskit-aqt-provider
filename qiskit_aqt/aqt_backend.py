from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration
import requests

from qiskit_aqt import aqt_job
from qiskit_aqt import qobj_to_aqt


class AQTBackend(BaseBackend):

    def __init__(self, provider=None):
        configuration = {
            'backend_name': 'aqt',
            'backend_version': '0.0.1',
            'url': 'https://www.aqt.eu/',
            'simulator': False,
            'local': False,
            'coupling_map': None,
            'description': 'Simulates only Hadamard gates',
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
        aqt_json = qobj_to_aqt.qobj_to_aqt(qobj)
        res = requests.post(self.configuration.url, data=aqt_json[0])
        if 'id' not in res:
            raise Exception
        job = aqt_job.AQTJob(self, res['id'])
        return job
