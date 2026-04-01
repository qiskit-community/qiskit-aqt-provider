from typing import Final, Optional
from uuid import UUID

import aqt_connector
import httpx
from aqt_connector import ArnicaApp
from aqt_connector.exceptions import (
    InvalidJobIDError,
    JobNotFoundError,
    NotAuthenticatedError,
    RequestError,
    UnknownServerError,
)
from aqt_connector.models.arnica.jobs import JobStatus as AQTJobStatus
from aqt_connector.models.arnica.response_bodies.jobs import JobState
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata
from qiskit_aqt_provider.aqt_job import _partial_qiskit_result_dict
from qiskit_aqt_provider.exceptions import (
    AQTApiError,
    AQTCredentialsError,
    AQTJobFailedError,
    AQTJobInvalidStateError,
    AQTRequestError,
    AQTValueError,
)


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
        *,
        timeout: Optional[float] = None,
        wait: float = 5,
    ) -> Result:
        """Blocks until the job finishes processing then returns the result.

        If an error occurs, the remaining circuits are not executed and the whole job is marked as failed.

        Raises:
            APIError: the operation failed on the target resource.
            AQTJobInvalidStateError: if the job was cancelled.
            AQTJobFailedError: if the job failed with an error.
            JobTimeoutError: If the job does not reach a final state before the specified timeout.

        Returns:
            The combined result of all circuit evaluations.
        """
        self.wait_for_final_state(timeout=timeout, wait=wait)

        if self._latest_state.status == AQTJobStatus.ERROR:
            error_message = self._latest_state.message or "Unknown error"
            raise AQTJobFailedError(f"Job failed: {error_message}")

        if self._latest_state.status != AQTJobStatus.FINISHED:
            raise AQTJobInvalidStateError(
                f"Unable to retrieve result for job {self.job_id()}. Job is {self._latest_state.status.lower()}."
            )

        result_dict = {
            "backend_name": self._properties.backend_name,
            "job_id": self.job_id(),
            "success": True,
            "results": [],
        }
        for circuit_index, circuit in enumerate(self._properties.circuits):
            samples = self._latest_state.result[circuit_index]
            result_dict["results"].append(
                _partial_qiskit_result_dict(samples, circuit, shots=self._properties.shots, memory=False)
            )

        return Result.from_dict(result_dict)

    def status(self) -> QiskitJobStatus:
        """Return the status of the job, among the values of ``JobStatus``.

        Raises:
            AQTCredentialsError: if the user is not authenticated and no access token is available.
            AQTCredentialsError: If the provided token is invalid or expired.
            AQTRequestError: If there is a network-related error during the request.
            AQTValueError: If the job with the specified ID does not exist.
            AQTValueError: If the provided job ID is not valid.
            AQTApiError: If the Arnica API encounters an internal error.
            AQTApiError: For any other unexpected errors.

        Returns:
            JobStatus: The current status of the job.
        """
        if self._latest_state.status in (AQTJobStatus.FINISHED, AQTJobStatus.ERROR, AQTJobStatus.CANCELLED):
            return self.STATUS_MAPPING[self._latest_state.status]

        try:
            self._latest_state = aqt_connector.fetch_job_state(self._arnica, UUID(self.job_id()))
        except NotAuthenticatedError as e:
            raise AQTCredentialsError(str(e)) from e
        except RequestError as e:
            raise AQTRequestError(str(e)) from e
        except (UnknownServerError, RuntimeError) as e:
            raise AQTApiError(str(e)) from e
        except (InvalidJobIDError, JobNotFoundError) as e:
            raise AQTValueError(str(e)) from e
        return self.STATUS_MAPPING.get(self._latest_state.status, QiskitJobStatus.QUEUED)
