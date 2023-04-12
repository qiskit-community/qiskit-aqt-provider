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
from typing import Any, Dict, List

from qiskit import QuantumCircuit

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
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    time_queued: float = field(default_factory=time.time)
    time_submitted: float = 0.0
    time_finished: float = 0.0
    error_message: str = "error"

    num_clbits: int = field(init=False)
    samples: List[List[int]] = field(init=False)

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

    def response_payload(self) -> Dict[str, Any]:
        """AQT API-compatible response for the current job status."""
        if self.status is JobStatus.QUEUED:
            return {"response": {"status": "queued"}}

        if self.status is JobStatus.ONGOING:
            return {"response": {"status": "ongoing"}}

        if self.status is JobStatus.FINISHED:
            return {"response": {"status": "finished", "result": self.samples}}

        if self.status is JobStatus.ERROR:
            return {"response": {"status": "error", "message": self.error_message}}

        if self.status is JobStatus.CANCELLED:
            return {"response": {"status": "cancelled"}}

        assert False, "unreachable"  # pragma: no cover


class TestResource(AQTResource):  # pylint: disable=too-many-instance-attributes
    """AQT computing resource with hooks for triggering different execution scenarios."""

    def __init__(
        self,
        *,
        min_queued_duration: float = 0.0,
        min_running_duration: float = 0.0,
        always_invalid: bool = False,
        always_invalid_status: bool = False,
        always_cancel: bool = False,
        always_error: bool = False,
        error_message: str = "",
    ) -> None:
        """Initialize the testing resource.

        Args:
            min_queued_duration: minimum time in seconds spent by all jobs in the QUEUED state
            min_running_duration: minimum time in seconds spent by all jobs in the ONGOING state
            always_invalid: always return invalid payloads when queried
            always_invalid_status: always return a valid payload but with an invalid status
            always_cancel: always cancel the jobs directly after submission
            always_error: always finish execution with an error
            error_message: the error message returned by failed jobs. Implies `always_error`.
        """
        super().__init__(
            AQTProvider(""),
            "test-resource",
            ApiResource(name="test-resource", id="test", type="simulator"),
        )
        self.jobs: Dict[str, TestJob] = {}

        self.min_queued_duration = min_queued_duration
        self.min_running_duration = min_running_duration
        self.always_invalid = always_invalid
        self.always_invalid_status = always_invalid_status
        self.always_cancel = always_cancel
        self.always_error = always_error or error_message
        self.error_message = error_message or str(uuid.uuid4())

    def submit(self, circuit: QuantumCircuit, shots: int) -> str:
        job = TestJob(circuit, shots, error_message=self.error_message)

        if self.always_cancel:
            job.cancel()

        self.jobs[job.job_id] = job
        return job.job_id

    def result(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs[job_id]
        now = time.time()

        if self.always_invalid:
            return {"invalid": "invalid"}

        if self.always_invalid_status:
            return {"response": {"status": "invalid"}}

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
