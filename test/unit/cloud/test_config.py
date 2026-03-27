from pathlib import Path
from typing import Optional

from qiskit_aqt_provider._cloud.config import ArnicaConfig


def test_it_calls_injected_path_resolver(tmp_path: Path) -> None:
    """The ArnicaConfig should call the injected path resolver with the provided store path."""
    called: Optional[Path] = None

    def resolver(arg: Optional[Path]) -> Path:
        nonlocal called
        called = arg
        return arg or tmp_path

    ArnicaConfig(store_path=tmp_path, store_path_resolver=resolver)
    assert called == tmp_path
