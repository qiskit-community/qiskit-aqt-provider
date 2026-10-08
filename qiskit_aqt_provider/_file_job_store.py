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

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import platformdirs

from qiskit_aqt_provider.exceptions import AQTJobNotFoundError, AQTJobPersistenceError


@dataclass(frozen=True)
class FileJobStore:
    """A filesystem adapter for the :class:`~qiskit_aqt_provider.persistence.JobStore` port."""

    root: Path | None = None

    def __post_init__(self) -> None:
        if self.root is None:
            root = Path(platformdirs.user_data_dir("qiskit_aqt_provider")) / "jobs"
        else:
            root = Path(self.root)
        object.__setattr__(self, "root", root)

    def save(self, job_id: str, payload: bytes) -> None:
        """Atomically save a payload under a job ID."""
        filepath = self._filepath(job_id)
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError as exc:
            raise AQTJobPersistenceError(f"Unable to create job store {filepath.parent}") from exc

        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(dir=filepath.parent, prefix=".job-", suffix=".tmp", delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
            temporary_path.chmod(0o600)
            temporary_path.replace(filepath)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise AQTJobPersistenceError(f"Unable to persist job {job_id}") from exc

    def load(self, job_id: str) -> bytes:
        """Load a payload by job ID."""
        filepath = self._filepath(job_id)
        try:
            return filepath.read_bytes()
        except FileNotFoundError as exc:
            raise AQTJobNotFoundError(f"No persisted job found for ID {job_id}") from exc
        except OSError as exc:
            raise AQTJobPersistenceError(f"Unable to read persisted job {job_id}") from exc

    def delete(self, job_id: str) -> None:
        """Delete a payload by job ID; missing payloads are ignored."""
        try:
            self._filepath(job_id).unlink(missing_ok=True)
        except OSError as exc:
            raise AQTJobPersistenceError(f"Unable to delete persisted job {job_id}") from exc

    def _filepath(self, job_id: str) -> Path:
        if (
            not isinstance(job_id, str)
            or not job_id
            or Path(job_id).name != job_id
            or "/" in job_id
            or "\\" in job_id
            or job_id in {".", ".."}
        ):
            raise AQTJobPersistenceError(f"Invalid job ID: {job_id}")
        if self.root is None:
            raise AQTJobPersistenceError("Job store has no root directory")
        return self.root / f"{job_id}.aqt-job"
