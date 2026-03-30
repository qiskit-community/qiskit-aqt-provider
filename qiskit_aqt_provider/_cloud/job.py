from typing import Final
from uuid import UUID

import aqt_connector
import httpx
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.jobs import JobStatus as AQTJobStatus
from aqt_connector.models.arnica.response_bodies.jobs import JobState
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata
from qiskit_aqt_provider.aqt_job import _partial_qiskit_result_dict


class CloudJob(JobV1):
    """A job representing the execution of one or more circuits on an AQT cloud resource."""

    STATUS_MAPPING: Final = {
        AQTJobStatus.CANCELLED: QiskitJobStatus.CANCELLED,
        AQTJobStatus.ERROR: QiskitJobStatus.ERROR,
        AQTJobStatus.FINISHED: QiskitJobStatus.DONE,
        AQTJobStatus.ONGOING: QiskitJobStatus.RUNNING,
        AQTJobStatus.QUEUED: QiskitJobStatus.QUEUED,
    }

    def __init__(self, arnica: ArnicaApp, api_client: httpx.Client, properties: CloudJobMetadata) -> None:
        """Initializes a cloud job with the given properties, HTTP client, and Arnica app instance."""
        self._arnica = arnica
        self._api_client = api_client
        self._properties = properties
        self._latest_state: JobState = properties.initial_state
        super().__init__(None, str(properties.job_id))

    def submit(self) -> None:
        """Do not call — submission is handled by the backend.

        This job object represents an execution that has already been submitted via backend.run(). Calling submit() is
        invalid and always raises a RuntimeError.

        Raises:
            RuntimeError: Job submission is performed by backend.run().
        """
        raise RuntimeError("Job is already submitted via backend.run()")

    def result(
        self,
    ) -> Result:
        """Blocks until the job finishes processing then returns the result.

        If an error occurs, the remaining circuits are not executed and the whole job is marked as failed.

        Returns:
            The combined result of all circuit evaluations.

        Raises:
            APIError: the operation failed on the target resource.

        """
        self.wait_for_final_state()

        success = False
        results = []

        if self._latest_state.status is AQTJobStatus.FINISHED:
            success = True
            for circuit_index, circuit in enumerate(self._properties.circuits):
                samples = self._latest_state.result[circuit_index]
                results.append(
                    _partial_qiskit_result_dict(samples, circuit, shots=self._properties.shots, memory=False)
                )

        error_message = self._latest_state.message if self._latest_state.status == AQTJobStatus.ERROR else None
        return Result.from_dict(
            {
                "backend_name": self._properties.backend_name,
                "qobj_id": id(self),
                "job_id": self.job_id(),
                "success": success,
                "results": results,
                # Pass error message as metadata
                "error": error_message,
            }
        )

    def status(self) -> QiskitJobStatus:
        """Return the status of the job, among the values of ``JobStatus``."""
        self._latest_state = aqt_connector.fetch_job_state(self._arnica, UUID(self.job_id()))
        return self.STATUS_MAPPING.get(self._latest_state.status, QiskitJobStatus.QUEUED)
