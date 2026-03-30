from typing import Callable

import httpx
from aqt_connector.models.arnica.response_bodies.jobs import SubmitJobResponse
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Result
from typing_extensions import TypeAlias

StateUpdateCallback: TypeAlias = Callable[[str, JobStatus, "CloudJob"], None]


class CloudJob(JobV1):
    def __init__(self, api_client: httpx.Client, job: SubmitJobResponse) -> None:
        self._api_client = api_client
        self._backend_name = job.job.resource_id
        self._latest_state = job.response
        super().__init__(None, str(job.job.job_id))

    def submit(self) -> None:
        """Submit the job to the backend for execution."""
        raise RuntimeError("Job is already submitted via backend.run()")

    def result(
        self,
    ) -> Result:
        """Return the results of the job."""
        raise NotImplementedError("CloudJob.result() is not yet implemented.")

    def status(self) -> JobStatus:
        """Return the status of the job, among the values of ``JobStatus``."""
        raise NotImplementedError("CloudJob.status() is not yet implemented.")
