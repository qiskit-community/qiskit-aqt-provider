# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import warnings

from .aqt_account import AQTAccount
from . import version

_PACKAGING_WARNING = False

AQT = AQTAccount()
__version__ = version.__version__

if not _PACKAGING_WARNING:
    warnings.warn("The qiskit.providers.aqt package will be renamed in the "
                  "next release. Starting in qiskit-aqt-provider 0.4.0 you "
                  "will need to change imports from 'qiskit.providers.aqt' to "
                  "'qiskit_aqt_provider'.", DeprecationWarning, stacklevel=2)
    _PACKAGING_WARNING = True
