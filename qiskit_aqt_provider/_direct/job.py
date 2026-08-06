from dataclasses import dataclass
from uuid import UUID

from qiskit.circuit import QuantumCircuit
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._transformers import partial_qiskit_result_dict
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.exceptions import AQTJobFailedError


@dataclass(frozen=True)
class DirectAccessJobMetadata:
    backend_name: str
    shots: int
    circuit: QuantumCircuit
    memory: bool


class DirectAccessJob(JobV1):
    """A job representing the execution of a circuit on an AQT direct access resource."""

    def __init__(self, api_client: DirectAccessAPIClient, job_id: UUID, metadata: DirectAccessJobMetadata) -> None:
        """Initializes a direct access job with the given job ID."""
        super().__init__(None, str(job_id))
        self._metadata = metadata
        self._api_client = api_client
        self._status: QiskitJobStatus = QiskitJobStatus.RUNNING

    def submit(self) -> None:
        """Do not call — submission is handled by the backend.

        This job object represents an execution that has already been submitted via backend.run(). Calling submit() is
        invalid and always raises a RuntimeError.

        Raises:
            RuntimeError: Job submission is performed by backend.run().
        """
        raise RuntimeError("Job is already submitted via backend.run()")

    def result(self, *, timeout: float | None = None) -> Result:
        """Blocks until the job finishes processing then returns the result.

        Args:
            timeout: The maximum number of seconds to wait for the job to finish. If None, wait indefinitely. The
                resource will however time out the request after 24 hours.

        Raises:
            APIError: the operation failed on the target resource.
            AQTJobInvalidStateError: if the job was cancelled.
            AQTJobFailedError: if the job failed with an error.
            qiskit.providers.exceptions.JobTimeoutError: If the job does not reach a final state before the specified timeout.

        Returns:
            The result of the circuit evaluation.
        """
        job_result = self._api_client.await_result(UUID(self.job_id()), timeout=timeout)

        if isinstance(job_result, api_models_direct.JobResultError):
            self._status = QiskitJobStatus.ERROR
            raise AQTJobFailedError("Job failed with error")

        result = {
            "backend_name": self._metadata.backend_name,
            "job_id": self._job_id,
            "success": True,
            "results": [
                partial_qiskit_result_dict(
                    job_result.result, self._metadata.circuit, shots=self._metadata.shots, memory=self._metadata.memory
                )
            ],
        }
        return Result.from_dict(result)

    def status(self) -> QiskitJobStatus:
        """Return the status of the job, among the values of :class:`~qiskit.providers.JobStatus`.

        Raises:
            AQTCredentialsError: if the user is not authenticated and no access token is available.
            AQTCredentialsError: If the provided token is invalid or expired.
            AQTRequestError: If there is a network-related error during the request.
            AQTValueError: If the job with the specified ID does not exist.
            AQTValueError: If the provided job ID is not valid.
            AQTApiError: If the API encounters an internal error.
            AQTApiError: For any other unexpected errors.

        Returns:
            qiskit.providers.JobStatus: The current status of the job.
        """
        return self._status
