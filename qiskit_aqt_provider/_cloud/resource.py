from typing import Optional, Union

import httpx
import pydantic as pdt
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.jobs import SubmitJobResponse
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails
from qiskit import QuantumCircuit
from qiskit.circuit.library import RGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2
from qiskit.transpiler import Target

from qiskit_aqt_provider._cloud.job import CloudJob
from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata
from qiskit_aqt_provider.api_client.errors import http_response_raise_for_status
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job


class CloudOptions(pdt.BaseModel):
    """Options for a cloud resource."""

    shots: pdt.PositiveInt = pdt.Field(default=100)


class CloudResource(BackendV2):
    """A resource in the AQT cloud, associated with a specific workspace."""

    MAX_SHOTS = 2000

    def __init__(
        self, arnica: ArnicaApp, api_client: httpx.Client, workspace_id: str, resource_details: ResourceDetails
    ) -> None:
        """Initializes a cloud resource with the given workspace and resource details.

        Qiskit allows to connect transpiler plugins for the scheduling and
        translation stage to be connected to backends
        [custom transpiler passes](https://quantum.cloud.ibm.com/docs/en/api/qiskit/providers#custom-transpiler-passes).
        The methods `get_scheduling_stage_plugin` and `get_translation_stage_plugin`
        are used to connect the appropriate transpiler plugins to AQT backends.
        """
        self._arnica = arnica
        self._api_client = api_client
        self.workspace_id = workspace_id
        self._resource_id = resource_details.id
        super().__init__(name=resource_details.id)
        self._update_target(resource_details.available_qubits)
        self._options = self._default_options()

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return self._resource_id

    @property
    def target(self) -> Target:
        """The resource's target."""
        return self._target

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return 50

    def get_scheduling_stage_plugin(self) -> str:
        """For usage of the custom scheduling stage plugin in the Qiskit transpiler."""
        return "aqt"

    def get_translation_stage_plugin(self) -> str:
        """For usage of the custom translation stage plugin in the Qiskit transpiler."""
        return "aqt"

    @classmethod
    def _default_options(cls) -> CloudOptions:
        """Get the default options.

        Returns:
            CloudOptions: The default options for this resource.
        """
        return CloudOptions()

    def run(self, circuits: Union[QuantumCircuit, list[QuantumCircuit]], *, shots: Optional[int] = None) -> CloudJob:
        """Run on the backend.

        This method returns a :class:`~qiskit.providers.Job` object that runs circuits.

        Args:
            circuits (QuantumCircuit or list[QuantumCircuit]): An individual or a list of :class:`.QuantumCircuit`
                objects to run on the backend.
            shots: The number of shots to use for the execution. If not specified, the default from the resource's
                options will be used.

        Returns:
            Job: The job object for the run.
        """
        if not isinstance(circuits, list):
            circuits = [circuits]

        shots = shots if shots is not None else self._options.shots
        if shots < 1 or shots > self.MAX_SHOTS:
            raise ValueError(f"Shots must be in the range [1, {self.MAX_SHOTS}].")

        request_payload = circuits_to_aqt_job(circuits, shots)
        resp = http_response_raise_for_status(
            self._api_client.post(
                f"/v1/submit/{self.workspace_id}/{self._resource_id}",
                content=request_payload.model_dump_json(),
            )
        )
        job_response = SubmitJobResponse.model_validate_json(resp.text)

        return CloudJob(
            self._arnica,
            self._api_client,
            CloudJobMetadata(
                job_id=job_response.job.job_id,
                shots=shots,
                backend_name=self.name,
                circuits=circuits,
                initial_state=job_response.response,
            ),
        )

    def _update_target(self, num_qubits: int) -> None:
        """Updates the target of this resource based on the given number of qubits."""
        theta = Parameter("θ")
        phi = Parameter("φ")
        lam = Parameter("λ")

        target = Target(num_qubits=num_qubits)
        target.add_instruction(RZGate(lam))
        target.add_instruction(RGate(theta, phi))
        target.add_instruction(RXXGate(theta))
        target.add_instruction(Measure())

        self._target = target
