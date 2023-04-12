#!/usr/bin/env python3

"""Extract the coverage target from the pyproject.toml file.

This is used by the Github workflows to write the coverage report comment on PRs.
"""

import shlex
import subprocess
from pathlib import Path

import tomlkit
import typer


def default_pyproject_path() -> Path:
    """Path to the 'pyproject.toml' file at the repository root."""
    repo_root = Path(
        subprocess.run(shlex.split("git rev-parse --show-toplevel"), capture_output=True)
        .stdout.strip()
        .decode("utf-8")
    )

    return repo_root / "pyproject.toml"


def main(pyproject_path: Path = typer.Argument(default_pyproject_path)) -> None:
    """Extract the coverage target from a pyproject.toml file.

    Read the 'pyproject.toml' file at `pyproject_path` and extract the
    'fail_under' field of the 'coverage' tool configuration.

    Args:
        pyproject_path: path of the pyproject.toml file to read.
    """
    with pyproject_path.open(encoding="utf-8") as fp:
        data = tomlkit.load(fp)
        print(
            float(data["tool"]["coverage"]["report"]["fail_under"])  # type: ignore[index, arg-type]
            / 100.0
        )


if __name__ == "__main__":
    typer.run(main)
