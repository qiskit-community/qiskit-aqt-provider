#!/usr/bin/env python3
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

import shlex
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import tomlkit
import typer

app = typer.Typer()


@lru_cache
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return Path(
        subprocess.run(  # noqa: S603
            shlex.split("git rev-parse --show-toplevel"),
            capture_output=True,
            check=True,
        )
        .stdout.strip()
        .decode("utf-8")
    ).absolute()


def default_schema_path() -> Path:
    """Default location of the API schema definition."""
    return repo_root() / "api" / "aqt_public.yml"


def default_models_path() -> Path:
    """Default destination of generated Pydantic models."""
    return repo_root() / "qiskit_aqt_provider" / "api_client" / "models_generated.py"


def generate_models(schema_path: Path, dest_path: Path, *, ruff_lint_extra_args: str = "") -> None:
    """Generate Pydantic models from a given schema.

    Args:
        schema_path: path to the file that contains the schema.
        dest_path: path to the file to write the generated models to.
        ruff_lint_extra_args: extra command-line arguments passed to the ruff linter.

    """
    dest_path.write_text(run_command(f"datamodel-codegen --input {schema_path}"))
    # First optimistically fix pydocstyle errors.
    # Addresses in particular D301 (escape-sequence-in-docstring).
    run_command(f"ruff check --fix --unsafe-fixes --select D {ruff_lint_extra_args} {dest_path}")
    run_command(f"ruff check {ruff_lint_extra_args} --fix {dest_path}")
    run_command(f"ruff format {dest_path}")


def run_command(cmd: str) -> str:
    """Run a command as subprocess.

    Args:
        cmd: command to execute.

    Returns:
        Content of the standard output produced by the command.

    Raises:
        typer.Exit: the command failed. The exit status code is 1.
    """
    try:
        proc = subprocess.run(  # noqa: S603
            shlex.split(cmd),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(e.stdout.decode())
        print(e.stderr.decode())
        print("-------------------------------------------------")
        print(f"'{cmd}' failed with error code: {e.returncode}")
        raise typer.Exit(code=1)

    return proc.stdout.decode()


@app.command()
def generate(
    schema_path: Path = typer.Argument(default_schema_path),
    models_path: Path = typer.Argument(default_models_path),
) -> None:
    """Generate Pydantic models from a schema.

    Any existing content in `models_path` is will be lost!

    Args:
        schema_path: path to the file that contains the schema
        models_path: path of the file to write the generated models to.
    """
    generate_models(schema_path, models_path)


@app.command()
def check(
    schema_path: Path = typer.Argument(default_schema_path),
    models_path: Path = typer.Argument(default_models_path),
) -> None:
    """Check if the Python models in `models_path` match the schema in `schema_path`.

    For the check to succeed, `models_path` must contain exactly what the
    generator produces with `schema_path` as input.
    """
    # Retrieve target-file-specific ignored linter rules.
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    pyproject = tomlkit.parse(pyproject_path.read_text())
    ignored_rules = pyproject["tool"]["ruff"]["lint"]["per-file-ignores"][  # type: ignore[index]
        str(models_path.relative_to(pyproject_path.parent))
    ]
    ruff_lint_extra_args = f"--ignore {','.join(ignored_rules)}"  # type: ignore[arg-type]

    with tempfile.NamedTemporaryFile(mode="w") as reference_models:
        filepath = Path(reference_models.name)
        generate_models(schema_path, filepath, ruff_lint_extra_args=ruff_lint_extra_args)

        run_command(f"diff -u {filepath} {models_path}")
        print("OK")


if __name__ == "__main__":
    app()
