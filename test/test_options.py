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

from collections.abc import Mapping

import pydantic as pdt
import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from qiskit_aqt_provider.aqt_options import AQTOptions


class OptionsFactory(ModelFactory[AQTOptions]):
    """Factory of random but well-formed options data."""

    __model__ = AQTOptions

    query_timeout_seconds = 10.0


def test_options_partial_update() -> None:
    """Check that `update_options` can perform partial updates."""
    options = AQTOptions()
    original = options.model_copy()

    options.update_options(with_progress_bar=not options.with_progress_bar)
    assert options.with_progress_bar is not original.with_progress_bar


def test_options_full_update() -> None:
    """Check that all options can be set with `update_options`."""
    options = AQTOptions()

    while True:
        update = OptionsFactory.build()
        if update != options:
            break

    options.update_options(**update.model_dump())
    assert options == update


def test_options_timeout_positive() -> None:
    """Check that the query_timeout_seconds options is validated to be strictly positive or null."""
    options = AQTOptions()
    options.query_timeout_seconds = 10.0  # works
    options.query_timeout_seconds = None  # works

    with pytest.raises(pdt.ValidationError, match="query_timeout_seconds must be None or > 0"):
        options.query_timeout_seconds = -2.0  # fails


def test_options_iteration() -> None:
    """Check that the AQTOptions type implements the Mapping ABC."""
    options = AQTOptions()
    assert isinstance(options, Mapping)
    assert len(options.model_dump()) == len(options)
    assert options.model_dump() == dict(options)
