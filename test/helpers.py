from uuid import UUID

from aqt_connector.models.arnica.jobs import BasicJobMetadata
from aqt_connector.models.arnica.response_bodies.jobs import (
    ResultResponse,
    RRCancelled,
    RRError,
    RRFinished,
    RROngoing,
    RRQueued,
)
from aqt_connector.models.operations import GateR, GateRXX, GateRZ, Measure, OperationModel
from pydantic import NonNegativeInt


class Operation:
    """Factories for API payloads of circuit operations."""

    @staticmethod
    def rz(*, phi: float, qubit: int) -> OperationModel:
        """RZ gate."""
        return OperationModel(root=GateRZ(operation="RZ", phi=phi, qubit=qubit))

    @staticmethod
    def r(*, phi: float, theta: float, qubit: int) -> OperationModel:
        """R gate."""
        return OperationModel(root=GateR(operation="R", phi=phi, theta=theta, qubit=qubit))

    @staticmethod
    def rxx(*, theta: float, qubits: list[NonNegativeInt]) -> OperationModel:
        """RXX gate."""
        return OperationModel(
            root=GateRXX(
                operation="RXX",
                theta=theta,
                qubits=qubits,
            )
        )

    @staticmethod
    def measure() -> OperationModel:
        """MEASURE operation."""
        return OperationModel(root=Measure(operation="MEASURE"))


class Response:
    """Factories for API response payloads."""

    @staticmethod
    def queued(*, job_id: UUID, workspace_id: str, resource_id: str) -> ResultResponse:
        """Queued job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRQueued(),
        )

    @staticmethod
    def ongoing(
        *, job_id: UUID, workspace_id: str, resource_id: str, finished_count: int
    ) -> ResultResponse:
        """Ongoing job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RROngoing(finished_count=finished_count),
        )

    @staticmethod
    def finished(
        *, job_id: UUID, workspace_id: str, resource_id: str, results: dict[str, list[list[int]]]
    ) -> ResultResponse:
        """Completed job with the given results."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRFinished(
                result={int(circuit_index): samples for circuit_index, samples in results.items()},
            ),
        )

    @staticmethod
    def error(*, job_id: UUID, workspace_id: str, resource_id: str, message: str) -> ResultResponse:
        """Failed job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRError(message=message),
        )

    @staticmethod
    def cancelled(*, job_id: UUID, workspace_id: str, resource_id: str) -> ResultResponse:
        """Cancelled job."""
        return ResultResponse(
            job=BasicJobMetadata(
                job_id=job_id,
                label="qiskit",
                resource_id=resource_id,
                workspace_id=workspace_id,
            ),
            response=RRCancelled(),
        )
