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

from collections import OrderedDict
from .aqt_provider import AQTProvider

AQT_AUTH_URL = "https://gateway.aqt.eu/marmot/sim/"


class AQTAccount:
    """Account for Alpine Quantum Technologies"""

    def __init__(self):
        self._credentials = None
        self._providers = OrderedDict()

    def enable_account(self, token, url=AQT_AUTH_URL):
        """Enable the AQT account using token, and optional URL.

        Args:
            token (str): The AQT token.
            url (str): The optional AQT connection url.
        """
        self._credentials = {'token': token, 'url': url}
        provider = AQTProvider(token)
        self._providers[provider.name] = provider
        return provider

    def providers(self, name=None):
        """Return a list of providers with optional filtering.

        Args:
            name (str): Name of provider

        Returns:
            list[AccountAQTProvider]: List of providers that match the
                specified criteria.
        """
        filters = []

        if name:
            filters.append(lambda pro_name: pro_name == name)

        providers = [provider for key, provider in self._providers.items()
                     if all(f(key) for f in filters)]

        return providers

    def get_provider(self, name):
        """Return the provider with the given name.
        Args:
            name (str): Name of provider to load.
        Returns:
            AccountProvider: provider that match the specified criteria.

        Raises:
            ValueError: If no provider matches the specified criteria,
                or more than one provider match the specified criteria.
        """
        providers = self.providers(name)

        if not providers:
            raise ValueError('No provider matching the criteria')
        if len(providers) > 1:
            raise ValueError('More than one provider matching the '
                             'criteria')

        return providers[0]
