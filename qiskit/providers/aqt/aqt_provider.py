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


from qiskit.provider.providerutils import filter_backends
from qiskit.providers import BaseProvider

from qiskit.providers.aqt.aqt_backend import AQTBackend


class AQTProvider(BaseProvider):
    """Provider for the Hadamard backend"""

    def __init__(self, access_token, url):
        super().__init__()

        self.access_token = access_token
        self.url = url
        # Populate the list of Hadamard backends
        self._backends = [AQTBackend(provider=self)]

    def backends(self, name=None, filters=None, **kwargs):
        # pylint: disable=arguments-differ
        backends = self._backends
        if name:
            backends = [
                backend for backend in backends if backend.name() == name]

        return filter_backends(backends, filters=filters, **kwargs)
