# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NoReturn,
    Optional,
    Union,
)

import numpy as np
from qiskit import QuantumCircuit
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.result.result import Result
from qiskit.utils.lazy_tester import contextlib
from tqdm import tqdm
from typing_extensions import Self, TypeAlias, assert_never

from qiskit_aqt_provider import persistence
from qiskit_aqt_provider.api_client import models_generated as api_models_generated
from qiskit_aqt_provider.api_client.models_direct import JobResultError
from qiskit_aqt_provider.aqt_options import AQTOptions
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job

if TYPE_CHECKING:  # pragma: no cover
    from qiskit_aqt_provider.aqt_resource import AQTDirectAccessResource, AQTResource


# Tags for the status of AQT API jobs


@dataclass
class JobFinished:
    """The job finished successfully."""

    status: ClassVar = JobStatus.DONE
    results: dict[int, list[list[int]]]


@dataclass
class JobFailed:
    """An error occurred during the job execution."""

    status: ClassVar = JobStatus.ERROR
    error: str


class JobQueued:
    """The job is queued."""

    status: ClassVar = JobStatus.QUEUED


@dataclass
class JobOngoing:
    """The job is running."""

    status: ClassVar = JobStatus.RUNNING
    finished_count: int


class JobCancelled:
    """The job was cancelled."""

    status = ClassVar = JobStatus.CANCELLED


JobStatusPayload: TypeAlias = Union[JobQueued, JobOngoing, JobFinished, JobFailed, JobCancelled]


@dataclass(frozen=True)
class Progress:
    """Progress information of a job."""

    finished_count: int
    """Number of completed circuits."""

    total_count: int
    """Total number of circuits in the job."""


@dataclass
class _MockProgressBar:
    """Minimal tqdm-compatible progress bar mock."""

    total: int
    """Total number of items in the job."""

    n: int = 0
    """Number of processed items."""

    def update(self, n: int = 1) -> None:
        """Update the number of processed items by `n`."""
        self.n += n

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
        /,
    ) -> None: ...


class AQTJob(JobV1):
    """Handle for quantum circuits jobs running on AQT cloud backends.

    Jobs contain one or more quantum circuits that are executed with a common
    set of options (see :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>`).

    Job handles should be retrieved from calls
    to :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>`, which immediately
    returns after submitting the job. The :meth:`result` method allows blocking until a job
    completes:

    >>> import qiskit
    >>> from qiskit.providers import JobStatus
    >>> from qiskit_aqt_provider import AQTProvider
    >>>
    >>> backend = AQTProvider("").get_backend("offline_simulator_no_noise")
    >>>
    >>> qc = qiskit.QuantumCircuit(1)
    >>> _ = qc.rx(3.14, 0)
    >>> _ = qc.measure_all()
    >>> qc = qiskit.transpile(qc, backend)
    >>>
    >>> job = backend.run(qc, shots=100)
    >>> result = job.result()
    >>> job.status() is JobStatus.DONE
    True
    >>> result.success
    True
    >>> result.get_counts()
    {'1': 100}
    """

    _backend: "AQTResource"

    def __init__(
        self,
        backend: "AQTResource",
        circuits: list[QuantumCircuit],
        options: AQTOptions,
    ) -> None:
        """Initialize an :class:`AQTJob` instance.

        .. tip:: :class:`AQTJob` instances should not be created directly. Use
          :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>`
          to submit circuits for execution and retrieve a job handle.

        Args:
            backend: backend to run the job on.
            circuits: list of circuits to execute.
            options: overridden resource options for this job.
        """
        super().__init__(backend, "")

        self.circuits = circuits
        self.options = options
        self.api_submit_payload = circuits_to_aqt_job(circuits, options.shots)

        self.status_payload: JobStatusPayload = JobQueued()

    @classmethod
    def restore(
        cls,
        job_id: str,
        *,
        access_token: Optional[str] = None,
        store_path: Optional[Path] = None,
        remove_from_store: bool = True,
    ) -> Self:
        """Restore a job handle from local persistent storage.

        .. warning:: The default local storage path depends on the `qiskit_aqt_provider`
            package version. Job persisted with a different package version will therefore
            **not** be found!

        .. hint:: If the job's execution backend is an offline simulator, the
            job is re-submitted to the simulation backend and the new job ID differs
            from the one passed to this function.

        Args:
            job_id: identifier of the job to retrieve.
            access_token: access token for the AQT cloud.
              See :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>`.
            store_path: local persistent storage directory.
              By default, use a standard cache directory.
            remove_from_store: if :data:`True`, remove the retrieved job's data from persistent
              storage after a successful load.

        Returns:
            A job handle for the passed `job_id`.

        Raises:
            JobNotFoundError: the target job was not found in persistent storage.
        """
        from qiskit_aqt_provider.aqt_provider import AQTProvider
        from qiskit_aqt_provider.aqt_resource import AQTResource, OfflineSimulatorResource

        store_path = persistence.get_store_path(store_path)
        data = persistence.Job.restore(job_id, store_path)

        # TODO: forward .env loading args?
        provider = AQTProvider(access_token)
        if data.resource.resource_type == "offline_simulator":
            # FIXME: persist with_noise_model and restore it
            resource = OfflineSimulatorResource(provider, data.resource, with_noise_model=False)
        else:
            resource = AQTResource(provider, data.resource)

        obj = cls(backend=resource, circuits=data.circuits.circuits, options=data.options)

        if data.resource.resource_type == "offline_simulator":
            # re-submit the job because we can't restore the backend state
            obj.submit()
        else:
            obj._job_id = job_id

        if remove_from_store:
            persistence.Job.remove_from_store(job_id, store_path)

        return obj

    def persist(self, *, store_path: Optional[Path] = None) -> Path:
        """Save this job to local persistent storage.

        .. warning:: Only jobs that have been submitted for execution
          can be persisted (a valid `job_id` is required).

        Args:
            store_path: local persistent storage directory.
              By default, use a standard cache directory.

        Returns:
            The path to the job data in local persistent storage.

        Raises:
            RuntimeError: the job was never submitted for execution.
        """
        if not self.job_id():
            raise RuntimeError("Can only persist submitted jobs.")

        store_path = persistence.get_store_path(store_path)
        data = persistence.Job(
            resource=self._backend.resource_id,
            circuits=persistence.Circuits(self.circuits),
            options=self.options,
        )

        return data.persist(self.job_id(), store_path)

    def submit(self) -> None:
        """Submit this job for execution.

        This operation is not blocking. Use :meth:`result()` to block until
        the job completes.

        Raises:
            RuntimeError: this job was already submitted.
            APIError: the operation failed on the remote portal.
        """
        if self.job_id():
            raise RuntimeError(f"Job already submitted (ID: {self.job_id()})")

        job_id = self._backend.submit(self)
        self._job_id = str(job_id)

    def status(self) -> JobStatus:
        """Query the job's status.

        Returns:
            Aggregated job status for all the circuits in this job.

        Raises:
            APIError: the operation failed on the remote portal.
        """
        payload = self._backend.result(uuid.UUID(self.job_id()))

        if isinstance(payload, api_models_generated.JobResponseRRQueued):
            self.status_payload = JobQueued()
        elif isinstance(payload, api_models_generated.JobResponseRROngoing):
            self.status_payload = JobOngoing(finished_count=payload.response.finished_count)
        elif isinstance(payload, api_models_generated.JobResponseRRFinished):
            self.status_payload = JobFinished(
                results={
                    int(circuit_index): [[sample.root for sample in shot] for shot in shots]
                    for circuit_index, shots in payload.response.result.items()
                }
            )
        elif isinstance(payload, api_models_generated.JobResponseRRError):
            self.status_payload = JobFailed(error=payload.response.message)
        elif isinstance(payload, api_models_generated.JobResponseRRCancelled):
            self.status_payload = JobCancelled()
        else:  # pragma: no cover
            assert_never(payload)

        return self.status_payload.status

    def progress(self) -> Progress:
        """Progress information for this job."""
        num_circuits = len(self.circuits)

        if isinstance(self.status_payload, JobQueued):
            return Progress(finished_count=0, total_count=num_circuits)

        if isinstance(self.status_payload, JobOngoing):
            return Progress(
                finished_count=self.status_payload.finished_count, total_count=num_circuits
            )

        # if the circuit is finished, failed, or cancelled, it is completed
        return Progress(finished_count=num_circuits, total_count=num_circuits)

    @property
    def error_message(self) -> Optional[str]:
        """Error message for this job (if any)."""
        if isinstance(self.status_payload, JobFailed):
            return self.status_payload.error

        return None

    def result(self) -> Result:
        """Block until all circuits have been evaluated and return the combined result.

        Success or error is signalled by the `success` field in the returned Result instance.

        Returns:
            The combined result of all circuit evaluations.

        Raises:
            APIError: the operation failed on the remote portal.
        """
        if self.options.with_progress_bar:
            context: Union[tqdm[NoReturn], _MockProgressBar] = tqdm(total=len(self.circuits))
        else:
            context = _MockProgressBar(total=len(self.circuits))

        with context as progress_bar:

            def callback(
                job_id: str,  # noqa: ARG001
                status: JobStatus,  # noqa: ARG001
                job: AQTJob,
            ) -> None:
                progress = job.progress()
                progress_bar.update(progress.finished_count - progress_bar.n)

            # one of DONE, CANCELLED, ERROR
            self.wait_for_final_state(
                timeout=self.options.query_timeout_seconds,
                wait=self.options.query_period_seconds,
                callback=callback,
            )

            # make sure the progress bar completes
            progress_bar.update(self.progress().finished_count - progress_bar.n)

        results = []

        if isinstance(self.status_payload, JobFinished):
            for circuit_index, circuit in enumerate(self.circuits):
                samples = self.status_payload.results[circuit_index]
                results.append(
                    _partial_qiskit_result_dict(
                        samples, circuit, shots=self.options.shots, memory=self.options.memory
                    )
                )

        return Result.from_dict(
            {
                "backend_name": self._backend.name,
                "backend_version": self._backend.version,
                "qobj_id": id(self.circuits),
                "job_id": self.job_id(),
                "success": self.status_payload.status is JobStatus.DONE,
                "results": results,
                # Pass error message as metadata
                "error": self.error_message,
            }
        )


class AQTDirectAccessJob(JobV1):
    """Handle for quantum circuits jobs running on direct-access AQT backends.

    Use
    :meth:`AQTDirectAccessResource.run
    <qiskit_aqt_provider.aqt_resource.AQTDirectAccessResource.run>`
    to get a handle and evaluate circuits on a direct-access backend.
    """

    _backend: "AQTDirectAccessResource"

    def __init__(
        self,
        backend: "AQTDirectAccessResource",
        circuits: list[QuantumCircuit],
        options: AQTOptions,
    ) -> None:
        """Initialize the :class:`AQTDirectAccessJob` instance.

        Args:
            backend: backend to run the job on.
            circuits: list of circuits to execute.
            options: overridden resource options for this job.
        """
        super().__init__(backend, "")

        self.circuits = circuits
        self.options = options
        self.api_submit_payload = circuits_to_aqt_job(circuits, options.shots)

        self._job_id = uuid.uuid4()
        self._status = JobStatus.INITIALIZING

    def submit(self) -> None:
        """No-op on direct-access backends."""

    def result(self) -> Result:
        """Iteratively submit all circuits and block until full completion.

        If an error occurs, the remaining circuits are not executed and the whole
        job is marked as failed.

        Returns:
            The combined result of all circuit evaluations.

        Raises:
            APIError: the operation failed on the target resource.
        """
        if self.options.with_progress_bar:
            context: Union[tqdm[NoReturn], _MockProgressBar] = tqdm(total=len(self.circuits))
        else:
            context = _MockProgressBar(total=len(self.circuits))

        result = {
            "backend_name": self._backend.name,
            "backend_version": self._backend.version,
            "qobj_id": id(self.circuits),
            "job_id": self.job_id(),
            "success": True,
            "results": [],
        }

        with context as progress_bar:
            for circuit_index, circuit in enumerate(self.circuits):
                api_circuit = self.api_submit_payload.payload.circuits[circuit_index]
                job_id = self._backend.submit(api_circuit)
                api_result = self._backend.result(
                    job_id, timeout=self.options.query_timeout_seconds
                )

                if isinstance(api_result.payload, JobResultError):
                    break

                result["results"].append(
                    _partial_qiskit_result_dict(
                        api_result.payload.result,
                        circuit,
                        shots=self.options.shots,
                        memory=self.options.memory,
                    )
                )

                progress_bar.update(1)
            else:  # no circuits in the job, or all executed successfully
                self._status = JobStatus.DONE
                return Result.from_dict(result)

        self._status = JobStatus.ERROR
        result["success"] = False
        return Result.from_dict(result)

    def status(self) -> JobStatus:
        """Query the job's status.

        Returns:
            Aggregated job status for all the circuits in this job.
        """
        return self._status


def _partial_qiskit_result_dict(
    samples: list[list[int]], circuit: QuantumCircuit, *, shots: int, memory: bool
) -> dict[str, Any]:
    """Build the Qiskit result dict for a single circuit evaluation.

    Args:
        samples: measurement outcome of the circuit evaluation.
        circuit: the evaluated circuit.
        shots: number of repetitions of the circuit evaluation.
        memory: whether to fill the classical memory dump field with the measurement results.

    Returns:
        Dict, suitable for Qiskit's `Result.from_dict` factory.
    """
    meas_map = _build_memory_mapping(circuit)

    data: dict[str, Any] = {"counts": _format_counts(samples, meas_map)}

    if memory:
        data["memory"] = ["".join(str(x) for x in reversed(states)) for states in samples]

    return {
        "shots": shots,
        "success": True,
        "status": JobStatus.DONE,
        "data": data,
        "header": {
            "memory_slots": circuit.num_clbits,
            "creg_sizes": [[reg.name, reg.size] for reg in circuit.cregs],
            "qreg_sizes": [[reg.name, reg.size] for reg in circuit.qregs],
            "name": circuit.name,
            "metadata": circuit.metadata or {},
        },
    }


def _build_memory_mapping(circuit: QuantumCircuit) -> dict[int, set[int]]:
    """Scan the circuit for measurement instructions and collect qubit to classical bits mappings.

    Qubits can be mapped to multiple classical bits, possibly in different classical registers.
    The returned map only maps qubits referenced in a `measure` operation in the passed circuit.
    Qubits not targeted by a `measure` operation will not appear in the returned result.

    Parameters:
        circuit: the `QuantumCircuit` to analyze.

    Returns:
        the translation map for all measurement operations in the circuit.

    Examples:
        >>> qc = QuantumCircuit(2)
        >>> qc.measure_all()
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        >>> qc = QuantumCircuit(2, 2)
        >>> _ = qc.measure([0, 1], [1, 0])
        >>> _build_memory_mapping(qc)
        {0: {1}, 1: {0}}

        >>> qc = QuantumCircuit(3, 2)
        >>> _ = qc.measure([0, 1], [0, 1])
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        >>> qc = QuantumCircuit(4, 6)
        >>> _ = qc.measure([0, 1, 2, 3], [2, 3, 4, 5])
        >>> _build_memory_mapping(qc)
        {0: {2}, 1: {3}, 2: {4}, 3: {5}}

        >>> qc = QuantumCircuit(3, 4)
        >>> qc.measure_all(add_bits=False)
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}, 2: {2}}

        >>> qc = QuantumCircuit(3, 3)
        >>> _ = qc.x(0)
        >>> _ = qc.measure([0], [2])
        >>> _ = qc.y(1)
        >>> _ = qc.measure([1], [1])
        >>> _ = qc.x(2)
        >>> _ = qc.measure([2], [0])
        >>> _build_memory_mapping(qc)
        {0: {2}, 1: {1}, 2: {0}}

        5 qubits in two registers:

        >>> from qiskit import QuantumRegister, ClassicalRegister
        >>> qr0 = QuantumRegister(2)
        >>> qr1 = QuantumRegister(3)
        >>> cr = ClassicalRegister(2)
        >>> qc = QuantumCircuit(qr0, qr1, cr)
        >>> _ = qc.measure(qr0, cr)
        >>> _build_memory_mapping(qc)
        {0: {0}, 1: {1}}

        Multiple mapping of a qubit:

        >>> qc = QuantumCircuit(3, 3)
        >>> _ = qc.measure([0, 1], [0, 1])
        >>> _ = qc.measure([0], [2])
        >>> _build_memory_mapping(qc)
        {0: {0, 2}, 1: {1}}
    """
    qu2cl: defaultdict[int, set[int]] = defaultdict(set)

    for instruction in circuit.data:
        if instruction.operation.name == "measure":
            for qubit, clbit in zip(instruction.qubits, instruction.clbits):
                qu2cl[circuit.find_bit(qubit).index].add(circuit.find_bit(clbit).index)

    return dict(qu2cl)


def _shot_to_int(
    fluorescence_states: list[int], qubit_to_bit: Optional[dict[int, set[int]]] = None
) -> int:
    """Format the detected fluorescence states from a single shot as an integer.

    This follows the Qiskit ordering convention, where bit 0 in the classical register is mapped
    to bit 0 in the returned integer. The first classical register in the original circuit
    represents the least-significant bits in the integer representation.

    An optional translation map from the quantum to the classical register can be applied.
    If given, only the qubits registered in the translation map are present in the return value,
    at the index given by the translation map.

    Parameters:
        fluorescence_states: detected fluorescence states for this shot
        qubit_to_bit: optional translation map from quantum register to classical register positions

    Returns:
        integral representation of the shot result, with the translation map applied.

    Examples:
       Without a translation map, the natural mapping is used (n -> n):

        >>> _shot_to_int([1])
        1

        >>> _shot_to_int([0, 0, 1])
        4

        >>> _shot_to_int([0, 1, 1])
        6

        Swap qubits 1 and 2 in the classical register:

        >>> _shot_to_int([1, 0, 1], {0: {0}, 1: {2}, 2: {1}})
        3

        If the map is partial, only the mapped qubits are present in the output:

        >>> _shot_to_int([1, 0, 1], {1: {2}, 2: {1}})
        2

        One can translate into a classical register larger than the
        qubit register.

        Warning: the classical register is always initialized to 0.

        >>> _shot_to_int([1], {0: {1}})
        2

        >>> _shot_to_int([0, 1, 1], {0: {3}, 1: {4}, 2: {5}}) == (0b110 << 3)
        True

        or with a map larger than the qubit space:

        >>> _shot_to_int([1], {0: {0}, 1: {1}})
        1

        Consider the typical example of two quantum registers (the second one contains
        ancilla qubits) and one classical register:

        >>> from qiskit import QuantumRegister, ClassicalRegister
        >>> qr_meas = QuantumRegister(2)
        >>> qr_ancilla = QuantumRegister(3)
        >>> cr = ClassicalRegister(2)
        >>> qc = QuantumCircuit(qr_meas, qr_ancilla, cr)
        >>> _ = qc.measure(qr_meas, cr)
        >>> tr_map = _build_memory_mapping(qc)

        We assume that a single shot gave the result:

        >>> ancillas = [1, 1, 0]
        >>> meas = [1, 0]

        Then the corresponding output is 0b01 (measurement qubits mapped straight
        to the classical register of length 2):

        >>> _shot_to_int(meas + ancillas, tr_map) == 0b01
        True

        One can overwrite qr_meas[1] with qr_ancilla[0]:

        >>> _ = qc.measure(qr_ancilla[0], cr[1])
        >>> tr_map = _build_memory_mapping(qc)
        >>> _shot_to_int(meas + ancillas, tr_map) == 0b11
        True
    """
    tr_map = qubit_to_bit or {}

    if tr_map:
        # allocate a zero-initialized classical register
        # TODO: support pre-initialized classical registers
        clbits = max(max(d) for d in tr_map.values()) + 1
        creg = [0] * clbits

        for src_index, dest_indices in tr_map.items():
            # the translation map could map more than just the measured qubits
            with contextlib.suppress(IndexError):
                for dest_index in dest_indices:
                    creg[dest_index] = fluorescence_states[src_index]
    else:
        creg = fluorescence_states.copy()

    return int((np.left_shift(1, np.arange(len(creg))) * creg).sum())


def _format_counts(
    samples: list[list[int]], qubit_to_bit: Optional[dict[int, set[int]]] = None
) -> dict[str, int]:
    """Format all shots results from a circuit evaluation.

    The returned dictionary is compatible with Qiskit's `ExperimentResultData`
    `counts` field.

    Keys are hexadecimal string representations of the detected states, with the
    optional `QuantumRegister` to `ClassicalRegister` applied. Values are the occurrences
    of the keys.

    Parameters:
        samples: detected qubit fluorescence states for all shots
        qubit_to_bit: optional quantum to classical register translation map

    Returns:
        collected counts, for `ExperimentResultData`.

    Examples:
        >>> _format_counts([[1, 0, 0], [0, 1, 0], [1, 0, 0]])
        {'0x1': 2, '0x2': 1}

        >>> _format_counts([[1, 0, 0], [0, 1, 0], [1, 0, 0]], {0: {2}, 1: {1}, 2: {0}})
        {'0x4': 2, '0x2': 1}
    """
    return dict(Counter(hex(_shot_to_int(shot, qubit_to_bit)) for shot in samples))
