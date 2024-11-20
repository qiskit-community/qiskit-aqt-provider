# (C) Copyright Alpine Quantum Technologies GmbH 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import importlib.metadata
import platform
from typing import Final, Optional

PACKAGE_VERSION: Final = importlib.metadata.version("qiskit-aqt-provider")
__version__: Final = PACKAGE_VERSION


def make_user_agent(name: str, *, extra: Optional[str] = None) -> str:
    """User-agent strings factory.

    Args:
        name: main name of the component to build a user-agent string for.
        extra: arbitrary extra data, appended to the default string.
    """
    user_agent = " ".join(
        [
            f"{name}/{PACKAGE_VERSION}",
            f"({platform.system()};",
            f"{platform.python_implementation()}/{platform.python_version()})",
        ]
    )

    if extra:
        user_agent += f" {extra}"

    return user_agent
