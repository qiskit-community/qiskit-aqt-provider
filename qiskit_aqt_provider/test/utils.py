# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Miscellaneous testing utilities."""

from typing import TypeVar, Union

import annotated_types
from pydantic import BaseModel

T = TypeVar("T", bound=annotated_types.BaseMetadata)


def get_field_constraint(
    model: Union[BaseModel, type[BaseModel]],
    field: str,
    constraint: type[T],
) -> T:
    """Retrieve a given piece of metadata from a Pydantic model field.

    Args:
        model: model owning the field.
        field: name of the field to inspect.
        constraint: type of the annotation to retrieve.

    Returns:
        instance of the first matching annotation.

    Raises:
        AttributeError: the passed model doesn't contain a field with the given name.
        ValueError: the target field doesn't contain a matching annotation.

    Examples:
       >>> from pydantic import BaseModel
       >>> from typing import Annotated
       >>> from annotated_types import Ge, Le
       >>>
       >>> class M(BaseModel):
       ...     x: Annotated[int, Ge(3)]
       ...
       >>> get_field_constraint(M, "x", Ge)
       Ge(ge=3)
       >>> get_field_constraint(M(x=4), "x", Ge)
       Ge(ge=3)
       >>> get_field_constraint(M, "x", Le)
       Traceback (most recent call last):
       ...
       ValueError: <class 'annotated_types.Le'>
       >>> get_field_constraint(M, "y", Ge)
       Traceback (most recent call last):
       ...
       AttributeError: y
    """
    if (field_info := model.model_fields.get(field)) is None:
        raise AttributeError(field)

    for metadata in field_info.metadata:
        if isinstance(metadata, constraint):
            return metadata

    raise ValueError(constraint)
