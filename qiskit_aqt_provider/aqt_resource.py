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

import warnings
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from qiskit import QuantumCircuit
from qiskit.circuit.library import RXGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2 as Backend
from qiskit.providers import Options as QiskitOptions
from qiskit.providers.models import BackendConfiguration
from qiskit.transpiler import Target
from qiskit_aer import AerJob, AerSimulator, noise
from typing_extensions import override

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_options import AQTOptions
from qiskit_aqt_provider.circuit_to_aqt import aqt_to_qiskit_circuit

if TYPE_CHECKING:  # pragma: no cover
    from qiskit_aqt_provider.aqt_provider import AQTProvider


TargetT = TypeVar("TargetT", bound=Target)


class UnknownOptionWarning(UserWarning):
    """An unknown option was passed to a backend's :meth:`run <AQTResource.run>` method."""


def make_transpiler_target(target_cls: Type[TargetT], num_qubits: int) -> TargetT:
    """Factory for transpilation targets of AQT resources.

    Args:
        target_cls: base class to use for the returned instance.
        num_qubits: maximum number of qubits supported by the resource.

    Returns:
        A Qiskit transpilation target for an AQT resource.
    """
    target: TargetT = target_cls(num_qubits=num_qubits)

    theta = Parameter("θ")
    lam = Parameter("λ")

    # configure the transpiler to use RX/RZ/RXX
    # the custom scheduling pass rewrites RX to R to comply to the Arnica API format.
    target.add_instruction(RZGate(lam))
    target.add_instruction(RXGate(theta))
    target.add_instruction(RXXGate(theta))
    target.add_instruction(Measure())

    return target


class AQTResource(Backend):
    """Qiskit backend for AQT quantum computing resources."""

    def __init__(
        self,
        provider: "AQTProvider",
        resource_id: api_models.ResourceId,
    ):
        """Initialize the backend.

        Args:
            provider: Qiskit provider that owns this backend.
            resource_id: description of resource to target.
        """
        super().__init__(name=resource_id.resource_id, provider=provider)

        self.resource_id = resource_id

        self._http_client = provider._http_client

        num_qubits = 20
        self._configuration = BackendConfiguration.from_dict(
            {
                "backend_name": resource_id.resource_name,
                "backend_version": 2,
                "url": provider.portal_url,
                "simulator": True,
                "local": False,
                "coupling_map": None,
                "description": "AQT trapped-ion device simulator",
                "basis_gates": ["r", "rz", "rxx"],  # the actual basis gates
                "memory": True,
                "n_qubits": num_qubits,
                "conditional": False,
                "max_shots": 200,
                "max_experiments": 1,
                "open_pulse": False,
                "gates": [
                    {"name": "rz", "parameters": ["theta"], "qasm_def": "TODO"},
                    {"name": "r", "parameters": ["theta", "phi"], "qasm_def": "TODO"},
                    {"name": "rxx", "parameters": ["theta"], "qasm_def": "TODO"},
                ],
            }
        )
        self._target = make_transpiler_target(Target, num_qubits)

        self._options = AQTOptions()

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
        resp = self._http_client.post(
            f"/submit/{self.resource_id.workspace_id}/{self.resource_id.resource_id}",
            json=job.api_submit_payload.dict(),
        )

        resp.raise_for_status()
        return api_models.Response.parse_obj(resp.json()).job.job_id

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
        resp = self._http_client.get(f"/result/{job_id}")
        resp.raise_for_status()
        return api_models.Response.parse_obj(resp.json())

    def configuration(self) -> BackendConfiguration:
        warnings.warn(
            "The configuration() method is deprecated and will be removed in a "
            "future release. Instead you should access these attributes directly "
            "off the object or via the .target attribute. You can refer to qiskit "
            "backend interface transition guide for the exact changes: "
            "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2",
            DeprecationWarning,
        )
        return self._configuration

    def properties(self) -> None:
        warnings.warn(  # pragma: no cover
            "The properties() method is deprecated and will be removed in a "
            "future release. Instead you should access these attributes directly "
            "off the object or via the .target attribute. You can refer to qiskit "
            "backend interface transition guide for the exact changes: "
            "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2",
            DeprecationWarning,
        )

    @property
    def max_circuits(self) -> int:
        return 2000

    @property
    def target(self) -> Target:
        return self._target

    @classmethod
    def _default_options(cls) -> QiskitOptions:
        return QiskitOptions()

    @property
    def options(self) -> AQTOptions:
        return self._options

    def get_scheduling_stage_plugin(self) -> str:
        return "aqt"

    def get_translation_stage_plugin(self) -> str:
        return "aqt"

    def run(self, circuits: Union[QuantumCircuit, List[QuantumCircuit]], **options: Any) -> AQTJob:
        """Submit circuits for execution on this resource.

        Args:
            circuits: circuits to execute
            options: overrides for this resource's options. Elements should be valid fields
              of the :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>` model.
              Unknown fields are ignored with a :class:`UnknownOptionWarning`.

        Returns:
            A handle to the submitted job.
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

        options_copy = self.options.copy()
        options_copy.update_options(**valid_options)

        job = AQTJob(
            self,
            circuits,
            options_copy,
        )
        job.submit()
        return job


def qubit_states_from_int(state: int, num_qubits: int) -> List[int]:
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
    job: AerJob
    circuits: List[QuantumCircuit]
    shots: int

    @property
    def job_id(self) -> UUID:
        return UUID(hex=self.job.job_id())


class OfflineSimulatorResource(AQTResource):
    """AQT-compatible offline simulator resource.

    Offline simulators expose the same interface and restrictions as hardware backends. If
    `with_noise_model` is true, a noise model approximating that of AQT hardware backends is used.

    .. tip::
      The simulator backend is provided by `Qiskit Aer <https://qiskit.org/ecosystem/aer/>`_. The
      Qiskit Aer resource is exposed for detailed detuning as the
      ``OfflineSimulatorResource.simulator`` attribute.
    """

    def __init__(
        self,
        provider: "AQTProvider",
        resource_id: api_models.ResourceId,
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

        self.job: Optional[SimulatorJob] = None

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

        self.job = SimulatorJob(
            job=self.simulator.run(circuits, shots=job.options.shots),
            circuits=job.circuits,
            shots=job.options.shots,
        )
        return self.job.job_id

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
        if self.job is None or job_id != self.job.job_id:
            raise api_models.UnknownJobError(str(job_id))

        qiskit_result = self.job.job.result()

        results: Dict[str, List[List[int]]] = {}
        for circuit_index, circuit in enumerate(self.job.circuits):
            samples: List[List[int]] = []

            # Use data()["counts"] instead of get_counts() to access the raw counts
            # in hexadecimal format.
            counts: Dict[str, int] = qiskit_result.data(circuit_index)["counts"]

            for hex_state, occurences in counts.items():
                samples.extend(
                    [
                        qubit_states_from_int(int(hex_state, 16), circuit.num_qubits)
                        for _ in range(occurences)
                    ]
                )

            results[str(circuit_index)] = samples

        return api_models.Response.finished(
            job_id=job_id,
            workspace_id=self.resource_id.workspace_id,
            resource_id=self.resource_id.resource_id,
            results=results,
        )
