# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Timeout utilities for tests."""

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager


@contextmanager
def timeout(seconds: float) -> Iterator[None]:
    """Limit the execution time of a context.

    Args:
        seconds: maximum execution time, in seconds.

    Raises:
        TimeoutError: the maximum execution time was reached.
    """
    stop = threading.Event()

    def counter(duration: float) -> None:
        if not stop.wait(duration):
            raise TimeoutError

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="timeout_") as pool:
        task = pool.submit(counter, duration=seconds)
        yield

        stop.set()
        task.result(1.0)
