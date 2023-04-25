# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Dummy resources for testing purposes."""

import enum
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List

from qiskit import QuantumCircuit

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import ApiResource, AQTResource


class JobStatus(enum.Enum):
    """AQT job lifecycle labels."""

    QUEUED = enum.auto()
    ONGOING = enum.auto()
    FINISHED = enum.auto()
    ERROR = enum.auto()
    CANCELLED = enum.auto()


@dataclass
class TestJob:  # pylint: disable=too-many-instance-attributes
    """Job state holder for the TestResource."""

    circuit: QuantumCircuit
    shots: int
    status: JobStatus = JobStatus.QUEUED
    job_id: uuid.UUID = field(default_factory=lambda: uuid.uuid4())
    time_queued: float = field(default_factory=time.time)
    time_submitted: float = 0.0
    time_finished: float = 0.0
    error_message: str = "error"

    num_clbits: int = field(init=False)
    samples: List[List[int]] = field(init=False)

    workspace: str = field(default="test-workspace", init=False)
    resource: str = field(default="test-resource", init=False)

    def __post_init__(self) -> None:
        """Calculate derived quantities."""
        self.num_clbits = self.circuit.num_clbits
        self.samples = [random.choices([0, 1], k=self.num_clbits) for _ in range(self.shots)]

    def submit(self) -> None:
        """Submit the job for execution."""
        self.time_submitted = time.time()
        self.status = JobStatus.ONGOING

    def finish(self) -> None:
        """The job execution finished successfully."""
        self.time_finished = time.time()
        self.status = JobStatus.FINISHED

    def error(self) -> None:
        """The job execution triggered an error."""
        self.time_finished = time.time()
        self.status = JobStatus.ERROR

    def cancel(self) -> None:
        """The job execution was cancelled."""
        self.time_finished = time.time()
        self.status = JobStatus.CANCELLED

    def response_payload(self) -> api_models.JobResponse:
        """AQT API-compatible response for the current job status."""
        if self.status is JobStatus.QUEUED:
            return api_models.Response.queued(
                job_id=self.job_id,
                workspace_id=self.workspace,
                resource_id=self.resource,
            )

        if self.status is JobStatus.ONGOING:
            return api_models.Response.ongoing(
                job_id=self.job_id,
                workspace_id=self.workspace,
                resource_id=self.resource,
            )

        if self.status is JobStatus.FINISHED:
            return api_models.Response.finished(
                job_id=self.job_id,
                workspace_id=self.workspace,
                resource_id=self.resource,
                samples=self.samples,
            )

        if self.status is JobStatus.ERROR:
            return api_models.Response.error(
                job_id=self.job_id,
                workspace_id=self.workspace,
                resource_id=self.resource,
                message=self.error_message,
            )

        if self.status is JobStatus.CANCELLED:
            return api_models.Response.cancelled(
                job_id=self.job_id, workspace_id=self.workspace, resource_id=self.resource
            )

        assert False, "unreachable"  # pragma: no cover  # noqa: PT015,S101


class TestResource(AQTResource):  # pylint: disable=too-many-instance-attributes
    """AQT computing resource with hooks for triggering different execution scenarios."""

    __test__ = False  # disable pytest collection

    def __init__(
        self,
        *,
        min_queued_duration: float = 0.0,
        min_running_duration: float = 0.0,
        always_cancel: bool = False,
        always_error: bool = False,
        error_message: str = "",
    ) -> None:
        """Initialize the testing resource.

        Args:
            min_queued_duration: minimum time in seconds spent by all jobs in the QUEUED state
            min_running_duration: minimum time in seconds spent by all jobs in the ONGOING state
            always_cancel: always cancel the jobs directly after submission
            always_error: always finish execution with an error
            error_message: the error message returned by failed jobs. Implies `always_error`.
        """
        super().__init__(
            AQTProvider(""),
            "test-workspace",
            ApiResource(name="test-resource", id="test", type="simulator"),
        )
        self.jobs: Dict[uuid.UUID, TestJob] = {}

        self.min_queued_duration = min_queued_duration
        self.min_running_duration = min_running_duration
        self.always_cancel = always_cancel
        self.always_error = always_error or error_message
        self.error_message = error_message or str(uuid.uuid4())

    def submit(self, circuit: QuantumCircuit, shots: int) -> uuid.UUID:
        job = TestJob(circuit, shots, error_message=self.error_message)

        if self.always_cancel:
            job.cancel()

        self.jobs[job.job_id] = job
        return job.job_id

    def result(self, job_id: uuid.UUID) -> api_models.JobResponse:
        job = self.jobs[job_id]
        now = time.time()

        if job.status is JobStatus.QUEUED and (now - job.time_queued) > self.min_queued_duration:
            job.submit()

        if (
            job.status is JobStatus.ONGOING
            and (now - job.time_submitted) > self.min_running_duration
        ):
            if self.always_error:
                job.error()
            else:
                job.finish()

        return job.response_payload()


class DummyResource(AQTResource):
    """A non-functional resource, for testing purposes."""

    def __init__(self, token: str) -> None:
        super().__init__(
            AQTProvider(token), "dummy", ApiResource(name="dummy", id="dummy", type="simulator")
        )
