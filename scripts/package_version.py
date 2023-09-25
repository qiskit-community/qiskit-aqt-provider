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

"""Utility script to update/check version numbers scattered across multiple files."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import tomlkit
import typer
from rich.console import Console

DOCS_VERSION_REGEX: Final = re.compile(r'(version|release)\s=\s"(\d+\.\d+\.\d+)"')


@dataclass(frozen=True)
class CommonArgs:
    pyproject_path: Path
    docs_conf_path: Path
    verbose: bool


def get_args(ctx: typer.Context) -> CommonArgs:
    """Typed getter for the common arguments stored in the typer context."""
    args = ctx.obj
    assert isinstance(args, CommonArgs)  # noqa: S101
    return args


if os.environ.get("CI"):
    console = Console(force_terminal=True, force_interactive=False)
else:
    console = Console()


app = typer.Typer()


def check_consistency(
    pyproject_path: Path,
    docs_conf_path: Path,
    *,
    verbose: bool,
    target_version: Optional[str],
) -> bool:
    """Check that version numbers are consistent.

    Args:
        pyproject_path: path to the pyproject.toml file.
        docs_conf_path: path to the Sphinx documentation configuration module.
        verbose: whether to show the detail of the found version numbers.
        target_version: if set, pass only if the detected version numbers are also
    consistent with this target version.

    Returns:
        Whether the detected version number are consistent.
    """
    pyproject = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    pyproject_version = str(pyproject["tool"]["poetry"]["version"])  # type: ignore[index]

    docs_conf = docs_conf_path.read_text(encoding="utf-8")

    docs_version, docs_release = "", ""
    for line in docs_conf.splitlines():
        result = DOCS_VERSION_REGEX.match(line.strip())
        if result:
            if result.group(1) == "version":
                docs_version = result.group(2)
            if result.group(1) == "release":
                docs_release = result.group(2)

        if docs_version and docs_release:
            break

    if verbose:
        if target_version is not None:
            console.print(f"Target version:         {target_version}")
        console.print(f"{pyproject_path}:         {pyproject_version}")
        console.print(f"{docs_conf_path} (version): {docs_version or '[red]not found'}")
        console.print(f"{docs_conf_path} (release): {docs_release or '[red]not found'}")

    consistent = pyproject_version == docs_version == docs_release
    if target_version is not None:
        consistent = consistent and (pyproject_version == target_version)

    if consistent:
        console.print("[bold green]PASS")
        return True

    console.print("[bold red]FAIL")
    return False


def bump_versions(pyproject_path: Path, docs_conf_path: Path, new_version: str) -> None:
    """Update version number to match a new target.

    Args:
        pyproject_path: path to the pyproject.toml file.
        docs_conf_path: path to the Sphinx documentation configuration module.
        new_version: target version to update to.
    """
    pyproject = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    pyproject["tool"]["poetry"]["version"] = new_version  # type: ignore[index]
    pyproject_path.write_text(tomlkit.dumps(pyproject), encoding="utf-8")

    docs_conf = docs_conf_path.read_text(encoding="utf-8")
    docs_conf = re.sub(r"version\s=\s\"(.*)\"", f'version = "{new_version}"', docs_conf)
    docs_conf = re.sub(r"release\s=\s\"(.*)\"", f'release = "{new_version}"', docs_conf)
    docs_conf_path.write_text(docs_conf, encoding="utf-8")


@app.command()
def check(ctx: typer.Context) -> None:
    """Check whether the package version numbers are consistent."""
    args = get_args(ctx)
    if not check_consistency(
        args.pyproject_path,
        args.docs_conf_path,
        verbose=args.verbose,
        target_version=None,
    ):
        raise typer.Exit(1)


@app.command()
def bump(ctx: typer.Context, new_version: str) -> None:
    """Update the package version."""
    args = get_args(ctx)

    bump_versions(args.pyproject_path, args.docs_conf_path, new_version)

    if not check_consistency(
        args.pyproject_path,
        args.docs_conf_path,
        verbose=args.verbose,
        target_version=new_version,
    ):
        raise typer.Exit(1)


@app.callback()
def common_args(
    ctx: typer.Context,
    pyproject_path: Path = typer.Option(Path("pyproject.toml")),
    docs_conf_path: Path = typer.Option(Path("docs/conf.py")),
    verbose: bool = False,
) -> None:
    """Command line arguments shared between multiple sub-commands."""
    ctx.obj = CommonArgs(
        pyproject_path=pyproject_path, docs_conf_path=docs_conf_path, verbose=verbose
    )


if __name__ == "__main__":
    app()
