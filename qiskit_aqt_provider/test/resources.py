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

import abc
import time
import uuid
from typing import Any, Dict, Final, Set, Tuple

from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import ApiResource, AQTResource


class AbstractDummyResource(AQTResource, abc.ABC):
    """Abstract dummy AQT resource."""

    def __init__(self) -> None:
        self.jobs: Set[str] = set()
        super().__init__(
            AQTProvider(""), "dummy", ApiResource(name="dummy", id="dummy", type="simulator")
        )

    def submit(self, circuit: QuantumCircuit, shots: int) -> str:
        job_id = str(uuid.uuid4())
        self.jobs.add(job_id)
        return job_id

    @abc.abstractmethod
    def result(self, job_id: str) -> Dict[str, Any]:
        ...  # pragma: no cover


class ErrorResource(AbstractDummyResource):
    """An AQT resource that always returns a well-formed error.

    The returned error string is unique between different instances.
    """

    def __init__(self) -> None:
        self.error_str: Final = str(uuid.uuid4())
        super().__init__()

    def result(self, job_id: str) -> Dict[str, Any]:
        self.jobs.remove(job_id)
        return {"response": {"status": "error", "message": self.error_str}}


class NonCompliantResource(AbstractDummyResource):
    """An AQT resource that always returns invalid payloads."""

    def result(self, job_id: str) -> Dict[str, Any]:
        self.jobs.remove(job_id)
        return {"invalid": "invalid"}


class SlowResource(AbstractDummyResource):
    """An AQT resource that has a configurable response delay."""

    def __init__(self, seconds_to_complete: float = 10.0) -> None:
        super().__init__()
        self.seconds_to_complete = seconds_to_complete
        self.jobs: Dict[str, Tuple[float, int]] = {}  # type: ignore[assignment]

    def submit(self, circuit: QuantumCircuit, shots: int) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = (time.time(), shots)
        return job_id

    def result(self, job_id: str) -> Dict[str, Any]:
        start_time, shots = self.jobs[job_id]
        elapsed_seconds = time.time() - start_time

        if elapsed_seconds < self.seconds_to_complete:
            return {"response": {"status": "ongoing"}}

        del self.jobs[job_id]
        return {"response": {"status": "finished", "result": [[1] * shots]}}
