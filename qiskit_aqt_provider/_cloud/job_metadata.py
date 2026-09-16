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

from uuid import UUID

import pydantic as pdt
from aqt_connector.models.arnica.response_bodies.jobs import JobState
from qiskit import QuantumCircuit


class CloudJobMetadata(pdt.BaseModel):
    model_config = pdt.ConfigDict(frozen=True, arbitrary_types_allowed=True)
    job_id: UUID
    shots: pdt.PositiveInt
    backend_name: str
    circuits: list[QuantumCircuit]
    initial_state: JobState
    memory: bool
