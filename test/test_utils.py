# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


import time
from contextlib import AbstractContextManager, nullcontext
from typing import Any

import pytest

from qiskit_aqt_provider.test.timeout import timeout


@pytest.mark.parametrize(
    ("max_duration", "duration", "expected"),
    [
        (1.0, 0.5, nullcontext()),
        (0.5, 1.0, pytest.raises(TimeoutError)),
    ],
)
def test_timeout_context(
    max_duration: float, duration: float, expected: AbstractContextManager[Any]
) -> None:
    """Basic test for the timeout context manager."""
    with expected:
        with timeout(max_duration):
            time.sleep(duration)
