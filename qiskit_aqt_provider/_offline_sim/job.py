# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

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
