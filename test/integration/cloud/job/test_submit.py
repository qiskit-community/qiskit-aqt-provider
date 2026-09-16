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

import pytest

from test.integration.cloud.job._helpers import make_job


def test_submit_raises_runtime_error() -> None:
    """It raises RuntimeError because jobs are submitted via backend.run()."""
    job = make_job()

    with pytest.raises(RuntimeError, match=r"Job is already submitted via backend.run\(\)"):
        job.submit()
