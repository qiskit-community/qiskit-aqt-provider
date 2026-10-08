# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import io
import json
from dataclasses import dataclass
from typing import Final, Literal, Protocol, runtime_checkable
from uuid import UUID

import pydantic as pdt
from qiskit import qpy
from qiskit.circuit import QuantumCircuit

from qiskit_aqt_provider._file_job_store import FileJobStore
from qiskit_aqt_provider.exceptions import (
    AQTJobBackendMismatchError,
    AQTJobCorruptError,
    AQTJobIncompatibleError,
    AQTJobNotFoundError,
    AQTJobPersistenceError,
)

__all__ = [
    "FileJobStore",
    "JobBackendMismatchError",
    "JobCorruptError",
    "JobIncompatibleError",
    "JobNotFoundError",
    "JobPersistenceError",
    "JobSnapshot",
    "JobStore",
    "decode_job",
    "delete_job",
    "encode_job",
    "persist_job",
    "restore_job",
]

JobKind = Literal["cloud", "direct"]
FORMAT_VERSION: Final = 1

JobPersistenceError = AQTJobPersistenceError
JobNotFoundError = AQTJobNotFoundError
JobCorruptError = AQTJobCorruptError
JobIncompatibleError = AQTJobIncompatibleError
JobBackendMismatchError = AQTJobBackendMismatchError


@runtime_checkable
class JobStore(Protocol):
    """Port used to save and retrieve opaque persisted job payloads."""

    def save(self, job_id: str, payload: bytes) -> None:
        """Save a payload under a job ID."""

    def load(self, job_id: str) -> bytes:
        """Load a payload by job ID."""

    def delete(self, job_id: str) -> None:
        """Delete a payload by job ID."""


@dataclass(frozen=True)
class JobSnapshot:
    """The state needed to recreate a submitted remote job handle."""

    job_id: UUID
    backend_kind: JobKind
    backend_name: str
    shots: int
    memory: bool
    circuits: list[QuantumCircuit]


class _JobHeader(pdt.BaseModel):
    job_id: UUID
    backend_kind: JobKind
    backend_name: str
    shots: pdt.PositiveInt
    memory: bool
    circuit_count: pdt.PositiveInt


def encode_job(snapshot: JobSnapshot) -> bytes:
    """Encode a job snapshot as a versioned JSON header followed by QPY circuits."""
    if not snapshot.circuits:
        raise ValueError("A persisted job must contain at least one circuit")

    header = {
        "format_version": FORMAT_VERSION,
        "job_id": str(snapshot.job_id),
        "backend_kind": snapshot.backend_kind,
        "backend_name": snapshot.backend_name,
        "shots": snapshot.shots,
        "memory": snapshot.memory,
        "circuit_count": len(snapshot.circuits),
    }
    circuit_data = io.BytesIO()
    qpy.dump(snapshot.circuits, circuit_data)
    return json.dumps(header, separators=(",", ":")).encode("utf-8") + b"\n" + circuit_data.getvalue()


def decode_job(payload: bytes) -> JobSnapshot:
    """Decode and validate a persisted job payload."""
    try:
        header_data, circuit_data = payload.split(b"\n", maxsplit=1)
        raw_header = json.loads(header_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise JobCorruptError("Persisted job has an invalid header") from exc

    if not isinstance(raw_header, dict):
        raise JobCorruptError("Persisted job header is not an object")
    if raw_header.get("format_version") != FORMAT_VERSION:
        raise JobIncompatibleError("Persisted job uses an unsupported format version")

    try:
        header = _JobHeader.model_validate(raw_header)
    except pdt.ValidationError as exc:
        raise JobCorruptError("Persisted job metadata is invalid") from exc

    try:
        circuits = qpy.load(io.BytesIO(circuit_data))
    except Exception as exc:
        raise JobCorruptError("Persisted job circuits cannot be decoded") from exc

    if not isinstance(circuits, list):
        raise JobCorruptError("Persisted job circuits are not a list")
    if len(circuits) != header.circuit_count or not all(isinstance(circuit, QuantumCircuit) for circuit in circuits):
        raise JobCorruptError("Persisted job contains an unexpected circuit payload")

    return JobSnapshot(
        job_id=header.job_id,
        backend_kind=header.backend_kind,
        backend_name=header.backend_name,
        shots=header.shots,
        memory=header.memory,
        circuits=circuits,
    )


def persist_job(snapshot: JobSnapshot, store: JobStore | None = None) -> None:
    """Persist a snapshot using the supplied store or the default file store."""
    _resolve_store(store).save(str(snapshot.job_id), encode_job(snapshot))


def restore_job(
    job_id: str,
    *,
    store: JobStore | None = None,
    backend_kind: JobKind,
    backend_name: str,
) -> JobSnapshot:
    """Load a snapshot and verify that it belongs to the requested backend."""
    snapshot = decode_job(_resolve_store(store).load(job_id))
    try:
        requested_id = UUID(job_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise JobPersistenceError(f"Invalid job ID: {job_id}") from exc

    if snapshot.job_id != requested_id:
        raise JobCorruptError("Persisted job ID does not match its storage key")
    if snapshot.backend_kind != backend_kind or snapshot.backend_name != backend_name:
        raise JobBackendMismatchError(
            f"Persisted job belongs to {snapshot.backend_kind} backend {snapshot.backend_name!r}"
        )
    return snapshot


def delete_job(job_id: str, store: JobStore | None = None) -> None:
    """Delete a persisted job using the supplied store or the default file store."""
    _resolve_store(store).delete(job_id)


def _resolve_store(store: JobStore | None) -> JobStore:
    return store if store is not None else FileJobStore()
