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

import typing
import warnings
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Optional,
    TypeVar,
    Union,
)
from uuid import UUID

import httpx
from qiskit import QuantumCircuit
from qiskit.circuit.library import RGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2 as Backend
from qiskit.providers import Options as QiskitOptions
from qiskit.providers.models import BackendConfiguration
from qiskit.transpiler import Target
from qiskit_aer import AerJob, AerSimulator, noise
from typing_extensions import TypeAlias, override

from qiskit_aqt_provider import api_client
from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.api_client.errors import http_response_raise_for_status
from qiskit_aqt_provider.aqt_job import AQTDirectAccessJob, AQTJob
from qiskit_aqt_provider.aqt_options import AQTDirectAccessOptions, AQTOptions
from qiskit_aqt_provider.circuit_to_aqt import aqt_to_qiskit_circuit
from qiskit_aqt_provider.versions import USER_AGENT_EXTRA

if TYPE_CHECKING:  # pragma: no cover
    from qiskit_aqt_provider.aqt_provider import AQTProvider


TargetT = TypeVar("TargetT", bound=Target)


class UnknownOptionWarning(UserWarning):
    """An unknown option was passed to a backend's :meth:`run <AQTResource.run>` method."""


def make_transpiler_target(target_cls: type[TargetT], num_qubits: int) -> TargetT:
    """Factory for transpilation targets of AQT resources.

    Args:
        target_cls: base class to use for the returned instance.
        num_qubits: maximum number of qubits supported by the resource.

    Returns:
        A Qiskit transpilation target for an AQT resource.
    """
    target: TargetT = target_cls(num_qubits=num_qubits)

    theta = Parameter("θ")
    phi = Parameter("φ")
    lam = Parameter("λ")

    target.add_instruction(RZGate(lam))
    target.add_instruction(RGate(theta, phi))
    target.add_instruction(RXXGate(theta))
    target.add_instruction(Measure())

    return target


_JobType = TypeVar("_JobType", AQTJob, AQTDirectAccessJob)

_OptionsType = TypeVar("_OptionsType", bound=AQTOptions)
"""Resource options model."""


class _ResourceBase(Generic[_OptionsType], Backend):
    """Common setup for AQT backends."""

    def __init__(
        self, provider: "AQTProvider", name: str, options_type: type[_OptionsType]
    ) -> None:
        """Initialize the Qiskit backend.

        Args:
            provider: Qiskit provider that owns this backend.
            name: name of the backend.
            options_type: options model. Must be default-initializable.
        """
        super().__init__(name=name, provider=provider)

        num_qubits = 20
        self._target = make_transpiler_target(Target, num_qubits)
        self._options = options_type()

        self._configuration = BackendConfiguration.from_dict(
            {
                "backend_name": name,
                "backend_version": 2,
                "url": str(provider._portal_client.portal_url),
                "simulator": True,
                "local": False,
                "coupling_map": None,
                "description": "AQT trapped-ion device simulator",
                "basis_gates": [name for name in self.target.operation_names if name != "measure"],
                "memory": True,
                "n_qubits": num_qubits,
                "conditional": False,
                "max_shots": self._options.max_shots(),
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [
                    {"name": "rz", "parameters": ["theta"], "qasm_def": "TODO"},
                    {"name": "r", "parameters": ["theta", "phi"], "qasm_def": "TODO"},
                    {"name": "rxx", "parameters": ["theta"], "qasm_def": "TODO"},
                ],
            }
        )

    def configuration(self) -> BackendConfiguration:
        """Legacy Qiskit backend configuration."""
        return self._configuration

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return 50

    @property
    def target(self) -> Target:
        """Transpilation target for this backend."""
        return self._target

    @classmethod
    def _default_options(cls) -> QiskitOptions:
        """Default backend options, in Qiskit format."""
        options_type = typing.get_args(cls.__orig_bases__[0])[0]
        return QiskitOptions(**options_type())

    @property
    def options(self) -> _OptionsType:
        """Configured backend options."""
        return self._options

    def get_scheduling_stage_plugin(self) -> str:
        """Name of the custom scheduling stage plugin for the Qiskit transpiler."""
        return "aqt"

    def get_translation_stage_plugin(self) -> str:
        """Name of the custom translation stage plugin for the Qiskit transpiler."""
        return "aqt"

    def _create_job(
        self,
        job_type: type[_JobType],
        circuits: Union[QuantumCircuit, list[QuantumCircuit]],
        **options: Any,
    ) -> _JobType:
        """Initialize a job handle of a given type.

        Helper function for the ``run()`` method implementations.

        Args:
            job_type: type of the job handle to initialize.
            circuits: circuits to execute when the job is submitted.
            options: backend options overrides.
        """
        if not isinstance(circuits, list):
            circuits = [circuits]

        valid_options = {key: value for key, value in options.items() if key in self.options}
        unknown_options = set(options) - set(valid_options)

        if unknown_options:
            for unknown_option in unknown_options:
                warnings.warn(
                    f"Option {unknown_option} is not used by this backend",
                    UnknownOptionWarning,
                    stacklevel=2,
                )

        options_copy = self.options.model_copy()
        options_copy.update_options(**valid_options)

        return job_type(
            self,
            circuits,
            options_copy,
        )


class AQTResource(_ResourceBase[AQTOptions]):
    """Qiskit backend for AQT cloud quantum computing resources.

    Use :meth:`AQTProvider.get_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_backend>`
    to retrieve backend instances.
    """

    def __init__(
        self,
        provider: "AQTProvider",
        resource_id: api_client.Resource,
    ) -> None:
        """Initialize the backend.

        Args:
            provider: Qiskit provider that owns this backend.
            resource_id: description of resource to target.
        """
        super().__init__(
            name=resource_id.resource_id,
            provider=provider,
            options_type=AQTOptions,
        )

        self._http_client: httpx.Client = provider._portal_client._http_client
        self.resource_id = resource_id

    def run(self, circuits: Union[QuantumCircuit, list[QuantumCircuit]], **options: Any) -> AQTJob:
        """Submit circuits for execution on this resource.

        Args:
            circuits: circuits to execute
            options: overrides for this resource's options. Elements should be valid fields
              of the :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>` model.
              Unknown fields are ignored with a :class:`UnknownOptionWarning`.

        Returns:
            A handle to the submitted job.
        """
        job = self._create_job(AQTJob, circuits, **options)
        job.submit()
        return job

    def submit(self, job: AQTJob) -> UUID:
        """Submit a quantum circuits job to the AQT resource.

        .. tip:: This is a low-level method. Use the :meth:`run` method to submit
            a job and retrieve a :class:`AQTJob <qiskit_aqt_provider.aqt_job.AQTJob>`
            handle.

        Args:
            job: the quantum circuits job to submit to the resource for execution.

        Returns:
            The unique identifier of the submitted job.
        """
        resp = http_response_raise_for_status(
            self._http_client.post(
                f"/submit/{self.resource_id.workspace_id}/{self.resource_id.resource_id}",
                json=job.api_submit_payload.model_dump(),
            )
        )
        return api_models.Response.model_validate(resp.json()).job.job_id

    def result(self, job_id: UUID) -> api_models.JobResponse:
        """Query the result for a specific job.

        .. tip:: This is a low-level method. Use the
            :meth:`AQTJob.result <qiskit_aqt_provider.aqt_job.AQTJob.result>`
            method to retrieve the result of a job described by a
            :class:`AQTJob <qiskit_aqt_provider.aqt_job.AQTJob>` handle.

        Parameters:
            job_id: The unique identifier for the target job.

        Returns:
            AQT API payload with the job results.
        """
        resp = http_response_raise_for_status(self._http_client.get(f"/result/{job_id}"))
        return api_models.Response.model_validate(resp.json())


class AQTDirectAccessResource(_ResourceBase[AQTDirectAccessOptions]):
    """Qiskit backend for AQT direct-access quantum computing resources.

    Use
    :meth:`AQTProvider.get_direct_access_backend
    <qiskit_aqt_provider.aqt_provider.AQTProvider.get_direct_access_backend>`
    to retrieve backend instances.
    """

    def __init__(
        self,
        provider: "AQTProvider",
        base_url: str,
    ) -> None:
        """Initialize the backend.

        Args:
            provider: Qiskit provider that owns the backend.
            base_url: URL of the direct-access interface.
        """
        super().__init__(
            provider=provider,
            name="direct-access",
            options_type=AQTDirectAccessOptions,
        )

        self._http_client = api_models.http_client(
            base_url=base_url, token=provider.access_token, user_agent_extra=USER_AGENT_EXTRA
        )

    def run(
        self, circuits: Union[QuantumCircuit, list[QuantumCircuit]], **options: Any
    ) -> AQTDirectAccessJob:
        """Prepare circuits for execution on this resource.

        .. warning:: The circuits are only evaluated during
          the :meth:`AQTDirectAccessJob.result
          <qiskit_aqt_provider.aqt_job.AQTDirectAccessJob.result>`
          call.

        Args:
            circuits: circuits to execute
            options: overrides for this resource's options. Elements should be valid fields
              of the :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>` model.
              Unknown fields are ignored with a :class:`UnknownOptionWarning`.

        Returns:
            A handle to the prepared job.
        """
        return self._create_job(AQTDirectAccessJob, circuits, **options)

    def submit(self, circuit: api_models.QuantumCircuit) -> UUID:
        """Submit a quantum circuit job to the AQT resource.

        Args:
            circuit: circuit to evaluate, in API format.

        Returns:
            The unique identifier of the submitted job.
        """
        resp = http_response_raise_for_status(
            self._http_client.put("/circuit", json=circuit.model_dump())
        )
        return UUID(resp.json())

    def result(self, job_id: UUID, *, timeout: Optional[float]) -> api_models_direct.JobResult:
        """Query the result of a specific job.

        Block until a result (success or error) is available.

        Args:
            job_id: unique identifier of the target job.
            timeout: query timeout, in seconds. Disabled if `None`.

        Returns:
            Job result, as API payload.
        """
        resp = http_response_raise_for_status(
            self._http_client.get(f"/circuit/result/{job_id}", timeout=timeout)
        )
        return api_models_direct.JobResult.model_validate(resp.json())


def qubit_states_from_int(state: int, num_qubits: int) -> list[int]:
    """Convert the Qiskit state representation to the AQT states samples one.

    Args:
        state: Qiskit quantum register state representation
        num_qubits: number of qubits in the register.

    Returns:
        AQT qubit states representation.

    Raises:
        ValueError: the passed state is too large for the passed register size.

    Examples:
        >>> qubit_states_from_int(0, 3)
        [0, 0, 0]

        >>> qubit_states_from_int(0b11, 3)
        [1, 1, 0]

        >>> qubit_states_from_int(0b01, 3)
        [1, 0, 0]

        >>> qubit_states_from_int(123, 7)
        [1, 1, 0, 1, 1, 1, 1]

        >>> qubit_states_from_int(123, 3)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Cannot represent state=123 on num_qubits=3.
    """
    if state.bit_length() > num_qubits:
        raise ValueError(f"Cannot represent {state=} on {num_qubits=}.")
    return [(state >> qubit) & 1 for qubit in range(num_qubits)]


@dataclass(frozen=True)
class SimulatorJob:
    """Data for a job running on a local simulator."""

    job: AerJob
    """Simulation backend job handle."""

    circuits: list[QuantumCircuit]
    """Quantum circuits to evaluate."""

    shots: int
    """Number of repetitions of each circuit."""

    @property
    def job_id(self) -> UUID:
        """The job's unique identifier."""
        return UUID(hex=self.job.job_id())


class OfflineSimulatorResource(AQTResource):
    """AQT-compatible offline simulator resource.

    Offline simulators expose the same interface and restrictions as hardware backends. If
    `with_noise_model` is true, a noise model approximating that of AQT hardware backends is used.

    .. tip::
      The simulator backend is provided by
      `Qiskit Aer <https://qiskit.github.io/qiskit-aer/>`_.
      The Qiskit Aer resource is exposed for detailed detuning as the
      ``OfflineSimulatorResource.simulator`` attribute.
    """

    def __init__(
        self,
        provider: "AQTProvider",
        resource_id: api_client.Resource,
        with_noise_model: bool,
    ) -> None:
        """Initialize an offline simulator resource.

        Args:
            provider: Qiskit provider that owns this backend.
            resource_id: identification of the offline simulator resource.
            with_noise_model: whether to configure a noise model in the simulator backend.
        """
        assert resource_id.resource_type == "offline_simulator"  # noqa: S101

        super().__init__(
            provider,
            resource_id=resource_id,
        )

        self.jobs: dict[UUID, SimulatorJob] = {}

        if not with_noise_model:
            noise_model = None
        else:
            # the transpiler lowers all operations to the gate set supported by the AQT API,
            # not to the resource target's one.
            noise_model = noise.NoiseModel(basis_gates=["r", "rz", "rxx"])
            noise_model.add_all_qubit_quantum_error(noise.depolarizing_error(0.003, 1), ["r"])
            noise_model.add_all_qubit_quantum_error(noise.depolarizing_error(0.01, 2), ["rxx"])

        self.simulator = AerSimulator(method="statevector", noise_model=noise_model)

    @property
    def with_noise_model(self) -> bool:
        """Whether the simulator includes a noise model."""
        return self.simulator.options.noise_model is not None

    @override
    def submit(self, job: AQTJob) -> UUID:
        """Submit a job for execution on the simulator.

        .. tip:: This is a low-level method. Use the :meth:`AQTResource.run()` method
            to submit a job and retrieve a :class:`AQTJob <qiskit_aqt_provider.aqt_job.AQTJob>`
            handle.

        Args:
            job: quantum circuits job to submit to the simulator.

        Returns:
            Unique identifier of the simulator job.
        """
        # Use the API payload such that the memory map is the same as that
        # of the remote devices.
        circuits = [
            aqt_to_qiskit_circuit(circuit.quantum_circuit, circuit.number_of_qubits)
            for circuit in job.api_submit_payload.payload.circuits
        ]

        sim_job = SimulatorJob(
            job=self.simulator.run(circuits, shots=job.options.shots),
            circuits=job.circuits,
            shots=job.options.shots,
        )

        # The Aer job is freshly created above, so its ID is unique
        # among the keys in self.jobs.
        self.jobs[sim_job.job_id] = sim_job

        return sim_job.job_id

    @override
    def result(self, job_id: UUID) -> api_models.JobResponse:
        """Query results for a simulator job.

        .. tip:: This is a low-level method. Use
            :meth:`AQTJob.result() <qiskit_aqt_provider.aqt_job.AQTJob.result>` instead.

        Args:
            job_id: identifier of the job to retrieve results for.

        Returns:
            AQT API payload with the job results.

        Raises:
            UnknownJobError: ``job_id`` doesn't correspond to a simulator job on this resource.
        """
        if (job := self.jobs.get(job_id)) is None:
            raise api_models.UnknownJobError(str(job_id))

        qiskit_result = job.job.result()

        results: dict[str, list[list[int]]] = {}
        for circuit_index, circuit in enumerate(job.circuits):
            samples: list[list[int]] = []

            # Use data()["counts"] instead of get_counts() to access the raw counts
            # in hexadecimal format.
            counts: dict[str, int] = qiskit_result.data(circuit_index)["counts"]

            for hex_state, occurrences in counts.items():
                samples.extend(
                    [
                        qubit_states_from_int(int(hex_state, 16), circuit.num_qubits)
                        for _ in range(occurrences)
                    ]
                )

            results[str(circuit_index)] = samples

        return api_models.Response.finished(
            job_id=job_id,
            workspace_id=self.resource_id.workspace_id,
            resource_id=self.resource_id.resource_id,
            results=results,
        )


AnyAQTResource: TypeAlias = Union[AQTResource, AQTDirectAccessResource]
"""Type of any remote or direct access resource."""
