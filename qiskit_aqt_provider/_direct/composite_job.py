from collections.abc import Callable, Sequence
from uuid import uuid4

import pydantic as pdt
from qiskit.providers import JobStatus, JobV1
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._direct.job import DirectAccessJob
from qiskit_aqt_provider.exceptions import (
    AQTJobFailedError,
)


class CompositeDirectAccessJobMetadata(pdt.BaseModel):
    model_config = pdt.ConfigDict(frozen=True)
    backend_name: str


class CompositeDirectAccessJob(JobV1):
    """A job representing the execution of multiple circuits on an AQT direct access resource."""

    def __init__(
        self, metadata: CompositeDirectAccessJobMetadata, job_submitters: Sequence[Callable[[], DirectAccessJob]]
    ) -> None:
        """Initializes a composite direct access job with the given circuits."""
        self._metadata = metadata
        self._job_submitters = list(job_submitters)
        self._job_id = uuid4()
        self._status = JobStatus.INITIALIZING
        self._result_dict = {
            "backend_name": self._metadata.backend_name,
            "job_id": self.job_id(),
            "success": True,
            "results": [],
        }
        self._current_job: DirectAccessJob | None = None

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

        If an error occurs, the remaining circuits are not executed and the whole job is marked as failed.

        Raises:
            AQTJobFailedError: if the job failed with an error.
            JobTimeoutError: If the job does not reach a final state before the specified timeout.

        Returns:
            The result of the circuit evaluation.
        """
        self._status = JobStatus.RUNNING
        while self._job_submitters:
            try:
                self._current_job = self._job_submitters.pop(0)()
                job_result = self._current_job.result(timeout=timeout)
            except AQTJobFailedError as e:
                self._status = JobStatus.ERROR
                raise e
            self._result_dict["results"].append(job_result.results[0].to_dict())

        self._status = JobStatus.DONE
        return Result.from_dict(self._result_dict)

    def status(self) -> QiskitJobStatus:
        """Return the status of the job, among the values of ``JobStatus``.

        Returns:
            JobStatus: The current status of the job.
        """
        return self._status
