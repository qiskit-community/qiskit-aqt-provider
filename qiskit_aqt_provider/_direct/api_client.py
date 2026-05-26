from uuid import UUID

import httpx
from aqt_connector.models.circuits import QuantumCircuit

from qiskit_aqt_provider.api_client import models_direct
from qiskit_aqt_provider.exceptions import AQTApiError, AQTRequestError


class DirectAccessAPIClient:
    """A client for the AQT direct access API."""

    def __init__(self, client: httpx.Client) -> None:
        """Initializes the API client with the given HTTP client."""
        self.is_closed = False
        self._api_client = client

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self._api_client.close()
        self.is_closed = True

    def fetch_available_qubits(self) -> int:
        """Fetches the number of available qubits."""
        qubit_response = self._api_client.get("/status/ions")
        qubit_response.raise_for_status()
        return models_direct.NumIons.model_validate_json(qubit_response.text).num_ions

    def fetch_name(self) -> str:
        """Fetches the resource's name."""
        name_response = self._api_client.get("/system/name")
        name_response.raise_for_status()
        return str(name_response.json())

    def submit_circuit(self, circuit: QuantumCircuit) -> UUID:
        """Submits a circuit for execution and returns the job ID."""
        try:
            resp = self._api_client.put("/circuit", content=circuit.model_dump_json())
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code > 499:  # noqa: PLR2004
                raise AQTApiError("Server error occurred while submitting circuit") from e
            raise AQTRequestError("Failed to submit circuit") from e

        return UUID(resp.json())

    def await_result(
        self, job_id: UUID, timeout: float | None = None
    ) -> models_direct.JobResultError | models_direct.JobResultFinished:
        """Waits for the result of a submitted job."""
        response = self._api_client.get(f"/circuit/result/{job_id}", timeout=timeout)
        response.raise_for_status()
        return models_direct.JobResult.model_validate_json(response.text).payload
