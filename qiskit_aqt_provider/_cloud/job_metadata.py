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
