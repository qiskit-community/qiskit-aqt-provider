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

import threading
import uuid
from collections import Counter, defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

import numpy as np
from qiskit import QuantumCircuit
from qiskit.providers import JobV1
from qiskit.providers.jobstatus import JobStatus
from qiskit.result.result import Result
from qiskit.utils.lazy_tester import contextlib

if TYPE_CHECKING:  # pragma: no cover
    from qiskit_aqt_provider.aqt_resource import AQTResource


# Tags for the status of AQT API jobs


@dataclass
class JobFinished:
    """The job finished successfully."""

    status: ClassVar = JobStatus.DONE
    samples: List[List[int]]


@dataclass
class JobFailed:
    """An error occurred during the job execution."""

    status: ClassVar = JobStatus.ERROR
    error: str


class JobQueued:
    """The job is queued."""

    status: ClassVar = JobStatus.QUEUED


class JobOngoing:
    """The job is running."""

    status: ClassVar = JobStatus.RUNNING


class JobCancelled:
    """The job was cancelled."""

    status = ClassVar = JobStatus.CANCELLED


class AQTJob(JobV1):
    _backend: "AQTResource"

    def __init__(
        self,
        backend: "AQTResource",
        circuits: List[QuantumCircuit],
        shots: int,
    ):
        """Initialize a job instance.

        Parameters:
            backend (BaseBackend): Backend that job was executed on.
            circuits (List[QuantumCircuit]): List of circuits to execute.
            shots (int): Number of repetitions per circuit.
        """
        super().__init__(backend, str(uuid.uuid4()))

        self.shots = shots
        self.circuits = circuits

        self._jobs: Dict[
            str, Union[JobFinished, JobFailed, JobQueued, JobOngoing, JobCancelled]
        ] = {}
        self._jobs_lock = threading.Lock()

    def submit(self) -> None:
        """Submits a job for execution."""
        # do not parallelize to guarantee that the order is preserved in the _jobs dict
        for circuit in self.circuits:
            self._submit_single(circuit, self.shots)

    def status(self) -> JobStatus:
        """Query the job's status.

        The job status is aggregated from the status of the individual circuits running
        on the AQT resource.

        Returns:
            JobStatus: aggregated job status for all the circuits in this job.

        Raises:
            RuntimeError: an unexpected error occurred while retrieving a circuit status.
        """
        # update the local job cache
        with ThreadPoolExecutor(thread_name_prefix="status_worker_") as pool:
            futures = [pool.submit(self._status_single, job_id) for job_id in self._jobs]

            for fut in as_completed(futures, timeout=10.0):
                if (exc := fut.exception()) is not None:
                    raise RuntimeError("Unexpected error while retrieving job status.") from exc

        return self._aggregate_status()

    def result(self) -> Result:
        """Block until all circuits have been evaluated and return the combined result.

        Success or error is signalled by the `success` field in the returned Result instance.

        In case of error, use `AQTJobNew.failed_jobs` to access the error messages of the
        failed circuit evaluations.

        Returns:
            The combined result of all circuit evaluations.
        """
        # one of DONE; CANCELLED, ERROR
        self.wait_for_final_state(
            timeout=self._backend.options.query_timeout_seconds,
            wait=self._backend.options.query_period_seconds,
        )

        agg_status = self._aggregate_status()

        results = []

        # jobs order is submission order
        for circuit, result in zip(self.circuits, self._jobs.values()):
            data: Dict[str, Any] = {}

            if isinstance(result, JobFinished):
                meas_map = _build_memory_mapping(circuit)
                data["counts"] = _format_counts(result.samples, meas_map)
                data["memory"] = [
                    "".join(str(x) for x in reversed(shots)) for shots in result.samples
                ]

            results.append(
                {
                    "shots": self.shots,
                    "success": result.status is JobStatus.DONE,
                    "status": result.status.value,
                    "data": data,
                    "header": {
                        "memory_slots": circuit.num_clbits,
                        "creg_sizes": [[reg.name, reg.size] for reg in circuit.cregs],
                        "qreg_sizes": [[reg.name, reg.size] for reg in circuit.qregs],
                        "name": circuit.name,
                        "metadata": circuit.metadata or {},
                    },
                }
            )

        return Result.from_dict(
            {
                "backend_name": self._backend.name,
                "backend_version": self._backend.version,
                "qobj_id": id(self.circuits),
                "job_id": self.job_id(),
                "success": agg_status is JobStatus.DONE,
                "results": results,
                # Pass individual circuit errors as metadata
                "errors": self.failed_jobs,
            }
        )

    @property
    def job_ids(self) -> Set[str]:
        """The AQT API identifiers of all the circuits evaluated in this Qiskit job."""
        return set(self._jobs)

    @property
    def failed_jobs(self) -> Dict[str, str]:
        """Map of failed job ids to error reports from the API."""
        with self._jobs_lock:
            return {
                job_id: payload.error
                for job_id, payload in self._jobs.items()
                if isinstance(payload, JobFailed)
            }

    def _submit_single(self, circuit: QuantumCircuit, shots: int) -> None:
        """Submit a single quantum circuit for execution on the backend.

        Parameters:
            circuit (QuantumCircuit): The quantum circuit to execute
            shots (int): Number of repetitions

        Returns:
            The AQT job identifier.
        """
        job_id = self._backend.submit(circuit, shots)
        with self._jobs_lock:
            self._jobs[job_id] = JobQueued()

    def _status_single(self, job_id: str) -> None:
        """Query the status of a single circuit execution.

        This method updates the internal life-cycle tracker.
        """
        payload = self._backend.result(job_id)
        response = payload["response"]

        with self._jobs_lock:
            if response["status"] == "finished":
                self._jobs[job_id] = JobFinished(samples=response["result"])
            elif response["status"] == "error":
                self._jobs[job_id] = JobFailed(error=str(response["message"]))
            elif response["status"] == "queued":
                self._jobs[job_id] = JobQueued()
            elif response["status"] == "ongoing":
                self._jobs[job_id] = JobOngoing()
            elif response["status"] == "cancelled":
                self._jobs[job_id] = JobCancelled()
            else:
                raise RuntimeError(f"API returned unknown job status: {response['status']}.")

    def _aggregate_status(self) -> JobStatus:
        """Aggregate the Qiskit job status from the status of the individual circuit evaluations."""
        # aggregate job status from individual circuits
        with self._jobs_lock:
            statuses = [payload.status for payload in self._jobs.values()]

        if any(s is JobStatus.ERROR for s in statuses):
            return JobStatus.ERROR

        if any(s is JobStatus.CANCELLED for s in statuses):
            return JobStatus.CANCELLED

        if any(s is JobStatus.RUNNING for s in statuses):
            return JobStatus.RUNNING

        if all(s is JobStatus.QUEUED for s in statuses):
            return JobStatus.QUEUED

        if all(s is JobStatus.DONE for s in statuses):
            return JobStatus.DONE

        # TODO: check for completeness
        return JobStatus.QUEUED


def _build_memory_mapping(circuit: QuantumCircuit) -> Dict[int, Set[int]]:
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
    field = namedtuple("field", "offset,size")

    # quantum memory map
    qregs = {}
    offset = 0
    for qreg in circuit.qregs:
        qregs[qreg] = field(offset, qreg.size)
        offset += qreg.size

    # classical memory map
    clregs = {}
    offset = 0
    for creg in circuit.cregs:
        clregs[creg] = field(offset, creg.size)
        offset += creg.size

    qu2cl: DefaultDict[int, Set[int]] = defaultdict(set)

    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name == "measure":
            for qubit, clbit in zip(instruction.qubits, instruction.clbits):
                qubit_index = qregs[qubit.register].offset + qubit.index
                clbit_index = clregs[clbit.register].offset + clbit.index
                qu2cl[qubit_index].add(clbit_index)

    return dict(qu2cl)


def _shot_to_int(
    fluorescence_states: List[int], qubit_to_bit: Optional[Dict[int, Set[int]]] = None
) -> int:
    """Format the detected fluorescence states from a single shot as an integer.

    This follows the Qiskit ordering convention, where bit 0 in the classical register is mapped
    to bit 0 in the returned integer. The first classical register in the original circuit
    represents the least-significant bits in the interger representation.

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
    samples: List[List[int]], qubit_to_bit: Optional[Dict[int, Set[int]]] = None
) -> Dict[str, int]:
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
