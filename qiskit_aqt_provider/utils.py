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

from typing import Callable, TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def map_exceptions(
    target_exc: type[BaseException], /, *, source_exc: tuple[type[BaseException]] = (Exception,)
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Map select exceptions to another exception type.

    Args:
        target_exc: exception type to map to
        source_exc: exception types to map to `target_exc`

    Examples:
        >>> @map_exceptions(ValueError)
        ... def func() -> None:
        ...     raise TypeError
        ...

        >>> func()  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError

        is equivalent to:

        >>> def func() -> None:
        ...     raise TypeError
        ...
        >>> try:
        ...     func()
        ... except Exception as e:
        ...     raise ValueError from e
        Traceback (most recent call last):
        ...  # doctest: +ELLIPSIS
        ValueError
    """

    def impl(func: Callable[P, T]) -> Callable[P, T]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except source_exc as e:
                raise target_exc from e

        return wrapper

    return impl
