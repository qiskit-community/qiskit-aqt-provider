# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""API models specific to the direct access API."""

import uuid
from typing import Annotated, Literal, Union

import pydantic as pdt
from typing_extensions import Self


class JobResultError(pdt.BaseModel):
    """Failed job result payload."""

    status: Literal["error"] = "error"


class JobResultFinished(pdt.BaseModel):
    """Successful job result payload."""

    status: Literal["finished"] = "finished"
    result: list[list[Annotated[int, pdt.Field(le=1, ge=0)]]]


class JobResult(pdt.BaseModel):
    """Result model on the direct access API."""

    job_id: uuid.UUID
    payload: Union[JobResultFinished, JobResultError] = pdt.Field(discriminator="status")

    @classmethod
    def create_error(cls, *, job_id: uuid.UUID) -> Self:
        """Create an error result (for tests).

        Args:
            job_id: job identifier.
        """
        return cls(job_id=job_id, payload=JobResultError())

    @classmethod
    def create_finished(cls, *, job_id: uuid.UUID, result: list[list[int]]) -> Self:
        """Create a success result (for tests).

        Args:
            job_id: job identifier.
            result: mock measured samples.
        """
        return cls(job_id=job_id, payload=JobResultFinished(result=result))
