from qiskit.exceptions import QiskitError
from qiskit.providers.exceptions import JobError


class AQTError(QiskitError):
    """Base class for errors raised by the AQT provider."""


class AQTJobError(AQTError, JobError):
    """Base class for errors raised by AQT cloud jobs."""


class AQTJobInvalidStateError(AQTJobError):
    """Error raised when an operation is attempted on a job in an invalid state."""


class AQTJobFailedError(AQTJobError):
    """Error raised when a job has failed."""


class AQTApiError(AQTError):
    """Errors that occur unexpectedly when querying the server."""


class AQTCredentialsError(AQTError):
    """Errors related to authentication and credentials for the AQT API."""


class AQTValueError(AQTError, ValueError):
    """Error raised when an invalid value is provided to a function or method."""


class AQTRequestError(AQTError):
    """Error raised due to issues with a request."""
