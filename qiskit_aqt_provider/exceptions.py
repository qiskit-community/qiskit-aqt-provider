# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

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
