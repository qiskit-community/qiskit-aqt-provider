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

import importlib.metadata
import platform
import uuid
from typing import Annotated, Final, Literal, Optional, Union

import httpx
import pydantic as pdt
from typing_extensions import Self

PACKAGE_VERSION: Final = importlib.metadata.version("qiskit-aqt-provider")
USER_AGENT: Final = " ".join(
    [
        f"aqt-api-client/{PACKAGE_VERSION}",
        f"({platform.system()}; {platform.python_implementation()}/{platform.python_version()})",
    ]
)


class NumIons(pdt.BaseModel):
    """Response model for the `GET /status/ions` query."""

    num_ions: int
    """Number of ions loaded on the direct-access resource."""


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


def http_client(
    *, base_url: str, token: str, user_agent_extra: Optional[str] = None
) -> httpx.Client:
    """A pre-configured httpx Client.

    Args:
        base_url: base URL of the server
        token: access token for the remote service.
        user_agent_extra: optional extra data to add to the user-agent string.
    """
    user_agent_extra = f" {user_agent_extra}" if user_agent_extra else ""
    headers = {"User-Agent": USER_AGENT + user_agent_extra}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return httpx.Client(headers=headers, base_url=base_url, timeout=10.0, follow_redirects=True)
