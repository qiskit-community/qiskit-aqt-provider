from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Result
from qiskit_aer.jobs import AerJob


class OfflineSimulatorJob(JobV1):
    def __init__(self, aer_job: AerJob) -> None:
        super().__init__(None, aer_job.job_id())
        self._aer_job = aer_job

    def submit(self) -> None:
        """Do not call — submission is handled by the backend.

        This job object represents an execution that has already been submitted via backend.run(). Calling submit() is
        invalid and always raises a RuntimeError.

        Raises:
            RuntimeError: Job submission is performed by backend.run().
        """
        raise RuntimeError("Job is already submitted via backend.run()")

    def status(self) -> JobStatus:
        """Return the status of the underlying Aer job."""
        return self._aer_job.status()

    def result(self, timeout: float | None = None) -> Result:
        return self._aer_job.result(timeout=timeout)
