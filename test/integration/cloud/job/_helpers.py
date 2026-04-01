import uuid
from typing import Optional

from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.jobs import JobState, RRQueued
from httpx import Client, MockTransport, Response
from qiskit import QuantumCircuit

from qiskit_aqt_provider._cloud.job import CloudJob
from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata

JOB_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def single_qubit_circuit() -> QuantumCircuit:
    """A minimal valid circuit (measure-only) that passes circuits_to_aqt_job."""
    qc = QuantumCircuit(1)
    qc.measure_all()
    return qc


def two_qubit_circuit() -> QuantumCircuit:
    """A minimal valid 2-qubit circuit (measure-only) that passes circuits_to_aqt_job."""
    qc = QuantumCircuit(2)
    qc.measure_all()
    return qc


def make_job(
    *, shots: int = 3, circuits: Optional[list[QuantumCircuit]] = None, initial_state: Optional[JobState] = None
) -> CloudJob:
    """Create a CloudJob with the given initial state, shots, and circuits."""
    if circuits is None:
        circuits = [single_qubit_circuit()]

    if initial_state is None:
        initial_state = RRQueued()

    return CloudJob(
        arnica=ArnicaApp(),
        api_client=Client(transport=MockTransport(lambda _: Response(404))),
        properties=CloudJobMetadata(
            job_id=JOB_ID,
            shots=shots,
            backend_name="r1",
            circuits=circuits,
            initial_state=initial_state,
        ),
    )
