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

import abc
import warnings
from copy import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

import httpx
from qiskit import QuantumCircuit
from qiskit.circuit.library import RXGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2 as Backend
from qiskit.providers import Options, Provider
from qiskit.providers.models import BackendConfiguration
from qiskit.transpiler import Target
from qiskit_aer import AerJob, AerSimulator
from typing_extensions import TypedDict

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job
from qiskit_aqt_provider.constants import REQUESTS_TIMEOUT


class ApiResource(TypedDict):
    name: str
    id: str
    type: str  # Literal["simulator", "device"]


class OptionalFloat(metaclass=abc.ABCMeta):
    """Runtime type for optional floating-point numbers.

    The type is permissive: integers are also allowed.

    Runtime type checking can be done with the `isinstance` builtin.
    See PEP-3119 for details.

    Examples:
        >>> isinstance(3.5, OptionalFloat)
        True
        >>> isinstance(3, OptionalFloat)
        True
        >>> isinstance(None, OptionalFloat)
        True
        >>> isinstance("abc", OptionalFloat)
        False
    """


OptionalFloat.register(int)
OptionalFloat.register(float)
OptionalFloat.register(type(None))


class Float(metaclass=abc.ABCMeta):
    """Permissive runtime type for floating-point numbers.

    The type is permissive: integers are also allowed.

    Runtime type checking can be done with the `isinstance` builtin.
    See PEP-3119 for details.

    Examples:
        >>> isinstance(3.5, Float)
        True
        >>> isinstance(3, Float)
        True
        >>> isinstance(None, Float)
        False
        >>> isinstance("abc", Float)
        False
    """


Float.register(int)
Float.register(float)


TargetT = TypeVar("TargetT", bound=Target)


def make_transpiler_target(target_cls: Type[TargetT], num_qubits: int) -> TargetT:
    """Factory for transpilation targets of AQT resources.

    Args:
        target_cls: base class to use for the returned instance
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
    def __init__(self, provider: Provider, workspace: str, resource: ApiResource):
        super().__init__(name="aqt_qasm_simulator", provider=provider)
        self._resource = resource
        self._workspace = workspace
        self.url = provider.portal_url
        self.headers = {
            "Authorization": f"Bearer {self._provider.access_token}",
            "SDK": "qiskit",
        }
        num_qubits = 20
        self._configuration = BackendConfiguration.from_dict(
            {
                "backend_name": resource["name"],
                "backend_version": 2,
                "url": self.url,
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

        self.options.set_validator("shots", (1, 200))
        self.options.set_validator("query_timeout_seconds", OptionalFloat)
        self.options.set_validator("query_period_seconds", Float)
        self.options.set_validator("with_progress_bar", bool)

    def submit(self, circuits: List[QuantumCircuit], shots: int) -> UUID:
        """Submit a quantum circuits job to the AQT backend.

        Args:
            circuits: circuits to execute
            shots: number of repetitions per circuit.

        Returns:
            The unique identifier of the submitted job.
        """
        payload = circuits_to_aqt_job(circuits, shots)

        url = f"{self.url}/submit/{self._workspace}/{self._resource['id']}"

        req = httpx.post(url, json=payload.dict(), headers=self.headers, timeout=REQUESTS_TIMEOUT)
        req.raise_for_status()
        return api_models.Response.parse_obj(req.json()).job.job_id

    def result(self, job_id: UUID) -> api_models.JobResponse:
        """Query the result for a specific job.

        Parameters:
            job_id: The unique identifier for the target job.

        Returns:
            Full returned payload.
        """
        url = f"{self.url}/result/{job_id}"
        req = httpx.get(url, headers=self.headers, timeout=REQUESTS_TIMEOUT)
        req.raise_for_status()
        return api_models.Response.parse_obj(req.json())

    def configuration(self) -> BackendConfiguration:
        warnings.warn(
            (
                "The configuration() method is deprecated and will be removed in a "
                "future release. Instead you should access these attributes directly "
                "off the object or via the .target attribute. You can refer to qiskit "
                "backend interface transition guide for the exact changes: "
                "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2"
            ),
            DeprecationWarning,
        )
        return self._configuration

    def properties(self) -> None:
        warnings.warn(  # pragma: no cover
            (
                "The properties() method is deprecated and will be removed in a "
                "future release. Instead you should access these attributes directly "
                "off the object or via the .target attribute. You can refer to qiskit "
                "backend interface transition guide for the exact changes: "
                "https://qiskit.org/documentation/apidoc/providers.html#backendv1-backendv2"
            ),
            DeprecationWarning,
        )

    @property
    def max_circuits(self) -> int:
        return 2000

    @property
    def target(self) -> Target:
        return self._target

    @classmethod
    def _default_options(cls) -> Options:
        return Options(
            shots=100,  # number of repetitions per circuit
            query_timeout_seconds=None,  # timeout for job status queries
            query_period_seconds=1,  # interval between job status queries
            with_progress_bar=True,  # show a progress bar when waiting for job results
        )

    def get_scheduling_stage_plugin(self) -> str:
        return "aqt"

    def get_translation_stage_plugin(self) -> str:
        return "aqt"

    def run(self, circuits: Union[QuantumCircuit, List[QuantumCircuit]], **options: Any) -> AQTJob:
        """Submit circuits for execution on this resource.

        Additional keywork arguments are treated as overrides for this resource's options.
        Keywords that are not valid options for this resource are ignored with a warning.

        Args:
            circuits: circuits to execute
            options: overrides for this resource's options.

        Returns:
            A job handle.
        """
        if not isinstance(circuits, list):
            circuits = [circuits]

        valid_options = {
            key: value for key, value in options.items() if key in self.options.__dict__
        }
        unknown_options = set(options) - set(valid_options)

        if unknown_options:
            for unknown_option in unknown_options:
                warnings.warn(
                    f"Option {unknown_option} is not used by this backend",
                    UserWarning,
                    stacklevel=2,
                )

        options_copy = copy(self.options)
        options_copy.update_options(**valid_options)

        job = AQTJob(
            self,
            circuits,
            options_copy.shots,
            with_progress_bar=options_copy.with_progress_bar,
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
    """AQT-compatible offline simulator resource that uses the Qiskit-Aer backend."""

    def __init__(self, provider: Provider, workspace: str, resource: ApiResource) -> None:
        if resource["type"] != "offline_simulator":
            raise ValueError(f"Cannot instantiate an OfflineSimulatorResource for {resource=}")

        # TODO: also support a noisy simulator
        super().__init__(provider, workspace, resource)

        self.job: Optional[SimulatorJob] = None
        self.simulator = AerSimulator(method="statevector")

    def submit(self, circuits: List[QuantumCircuit], shots: int) -> UUID:
        """Submit circuits for execution on the simulator.

        Args:
            circuits: circuits to execute
            shots: number of repetitions per circuit.

        Returns:
            Unique identifier of the simulator job.
        """
        self.job = SimulatorJob(
            job=self.simulator.run(circuits, shots=shots),
            circuits=circuits,
            shots=shots,
        )
        return self.job.job_id

    def result(self, job_id: UUID) -> api_models.JobResponse:
        """Query results for a simulator job.

        Args:
            job_id: identifier of the job to retrieve results for.

        Returns:
            AQT API payload with the job results.

        Raises:
            UnknownJobError: the passed identifier doesn't correspond to a simulator job
            on this resource.
        """
        if self.job is None or job_id != self.job.job_id:
            raise api_models.UnknownJobError(str(job_id))

        qiskit_result = self.job.job.result()

        results: Dict[str, List[List[int]]] = {}
        for circuit_index, circuit in enumerate(self.job.circuits):
            samples: List[List[int]] = []

            # Use data()["counts"] instead of get_counts() to access the raw counts
            # instead of the classical memory-mapped ones.
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
            workspace_id=self._workspace,
            resource_id=self._resource["id"],
            results=results,
        )
