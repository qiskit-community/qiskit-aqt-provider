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

"""Pytest dynamic configuration."""

import hypothesis

hypothesis.settings.register_profile(
    "default",
    deadline=None,  # Account for slower CI workers
    print_blob=True,  # Always print code to use with @reproduce_failure
)

pytest_plugins = [
    "pytest_qiskit_aqt",
]
