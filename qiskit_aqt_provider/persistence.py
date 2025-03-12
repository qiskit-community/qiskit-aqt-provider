# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import base64
import io
import typing
from pathlib import Path
from typing import Any, Optional, Union

import platformdirs
import pydantic as pdt
from pydantic import ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from qiskit import qpy
from qiskit.circuit import QuantumCircuit
from typing_extensions import Self

from qiskit_aqt_provider.api_client import Resource
from qiskit_aqt_provider.aqt_options import AQTOptions
from qiskit_aqt_provider.utils import map_exceptions
from qiskit_aqt_provider.versions import QISKIT_AQT_PROVIDER_VERSION


class JobNotFoundError(Exception):
    """A job was not found in persistent storage."""


class Circuits:
    """Custom Pydantic type to persist and restore lists of Qiskit circuits.

    Serialization of :class:`QuantumCircuit <qiskit.circuit.QuantumCircuit>` instances is
    provided by :mod:`qiskit.qpy`.
    """

    def __init__(self, circuits: list[QuantumCircuit]) -> None:
        """Initialize a container filled with the given circuits."""
        self.circuits = circuits

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Setup custom validator, to turn this class into a pydantic model."""
        return core_schema.no_info_plain_validator_function(function=cls.validate)

    @classmethod
    def validate(cls, value: Union[Self, str]) -> Self:
        """Parse the base64-encoded :mod:`qiskit.qpy` representation of a list of quantum circuits.

        Because initializing a Pydantic model also triggers validation, this parser accepts
        already formed instances of this class and returns them unvalidated.
        """
        if isinstance(value, Circuits):  # self bypass
            return typing.cast(Self, value)

        if not isinstance(value, str):
            raise ValueError(f"Expected string, received {type(value)}")

        data = base64.b64decode(value.encode("ascii"))
        buf = io.BytesIO(data)
        obj = qpy.load(buf)

        if not isinstance(obj, list):
            obj = [obj]

        for n, qc in enumerate(obj):
            if not isinstance(qc, QuantumCircuit):
                raise ValueError(f"Object at position {n} is not a QuantumCircuit: {type(qc)}")

        return cls(circuits=obj)

    @classmethod
    def json_encoder(cls, value: Self) -> str:
        """Return a base64-encoded QPY representation of the held list of circuits."""
        buf = io.BytesIO()
        qpy.dump(value.circuits, buf)
        return base64.b64encode(buf.getvalue()).decode("ascii")


class Job(pdt.BaseModel):
    """Model for job persistence in local storage."""

    model_config = ConfigDict(frozen=True, json_encoders={Circuits: Circuits.json_encoder})

    resource: Resource
    circuits: Circuits
    options: AQTOptions

    @classmethod
    @map_exceptions(JobNotFoundError, source_exc=(FileNotFoundError,))
    def restore(cls, job_id: str, store_path: Path) -> Self:
        """Load data for a job by ID from local storage.

        Args:
            job_id: identifier of the job to restore.
            store_path: path to the local storage directory.

        Raises:
            JobNotFoundError: no job with the given identifier is stored in the local storage.
        """
        data = cls.filepath(job_id, store_path).read_text("utf-8")
        return cls.model_validate_json(data)

    def persist(self, job_id: str, store_path: Path) -> Path:
        """Persist the job data to the local storage.

        Args:
            job_id: storage key for this job data.
            store_path: path to the local storage directory.

        Returns:
            The path of the persisted data file.
        """
        filepath = self.filepath(job_id, store_path)
        filepath.write_text(self.model_dump_json(), "utf-8")
        return filepath

    @classmethod
    def remove_from_store(cls, job_id: str, store_path: Path) -> None:
        """Remove persisted job data from the local storage.

        This function also succeeds if there is no data under `job_id`.

        Args:
            job_id: storage key for the data to delete.
            store_path: path to the local storage directory.
        """
        cls.filepath(job_id, store_path).unlink(missing_ok=True)

    @classmethod
    def filepath(cls, job_id: str, store_path: Path) -> Path:
        """Path of the file to store data under a given key in local storage.

        Args:
            job_id: storage key for the data.
            store_path: path to the local storage directory.
        """
        return store_path / job_id


def get_store_path(override: Optional[Path] = None) -> Path:
    """Resolve the local persistence store path.

    By default, this is the user cache directory for this package.
    Different cache directories are used for different package versions.

    Args:
        override: if given, return this override instead of the default path.

    Returns:
       Path for the persistence store. Ensured to exist.
    """
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        return override

    return Path(
        platformdirs.user_cache_dir(
            "qiskit_aqt_provider",
            version=QISKIT_AQT_PROVIDER_VERSION,
            ensure_exists=True,
        )
    )
