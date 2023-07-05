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
from collections import Counter, defaultdict, namedtuple
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    NoReturn,
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
from tqdm import tqdm
from typing_extensions import Self, TypeAlias, assert_never

from qiskit_aqt_provider import api_models_generated
from qiskit_aqt_provider.aqt_options import AQTOptions

if TYPE_CHECKING:  # pragma: no cover
    from qiskit_aqt_provider.aqt_resource import AQTResource


# Tags for the status of AQT API jobs


@dataclass
class JobFinished:
    """The job finished successfully."""

    status: ClassVar = JobStatus.DONE
    results: Dict[int, List[List[int]]]


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

    def __exit__(*args) -> None:
        ...


class AQTJob(JobV1):
    _backend: "AQTResource"

    def __init__(
        self,
        backend: "AQTResource",
        circuits: List[QuantumCircuit],
        options: AQTOptions,
    ):
        """Initialize a job instance.

        Args:
            backend: backend to run the job on
            circuits: list of circuits to execute
            options: overridden resource options for this job.
        """
        super().__init__(backend, "")

        self.circuits = circuits
        self.options = options
        self.status_payload: JobStatusPayload = JobQueued()

    def submit(self) -> None:
        """Submit this job for execution.

        Raises:
            RuntimeError: this job was already submitted.
        """
        if self.job_id():
            raise RuntimeError(f"Job already submitted (ID: {self.job_id()})")

        job_id = self._backend.submit(self.circuits, self.options.shots)
        self._job_id = str(job_id)

    def status(self) -> JobStatus:
        """Query the job's status.

        Returns:
            JobStatus: aggregated job status for all the circuits in this job.
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
                meas_map = _build_memory_mapping(circuit)
                data: Dict[str, Any] = {
                    "counts": _format_counts(samples, meas_map),
                }

                if self.options.memory:
                    data["memory"] = [
                        "".join(str(x) for x in reversed(states)) for states in samples
                    ]

                results.append(
                    {
                        "shots": self.options.shots,
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
