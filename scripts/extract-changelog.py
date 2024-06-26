#!/usr/bin/env python3

import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Final, Optional

import typer
from mistletoe import Document, block_token
from mistletoe.base_renderer import BaseRenderer

REVISION_HEADER_LEVEL: Final = 2
HEADER_REGEX: Final = re.compile(r"([a-z-]+)\s+(v\d+\.\d+\.\d+)")


class Renderer(BaseRenderer):
    """Markdown renderer."""

    def render_list_item(self, token: block_token.ListItem) -> str:
        """Tweak lists rendering. Use '*' as item marker."""
        return f"* {self.render_inner(token)}\n"


def default_changelog_path() -> Path:
    """Path to the 'CHANGELOG.md' file at the repository root."""
    repo_root = Path(
        subprocess.run(  # noqa: S603
            shlex.split("git rev-parse --show-toplevel"),
            capture_output=True,
            check=True,
        )
        .stdout.strip()
        .decode("utf-8")
    )

    return repo_root / "CHANGELOG.md"


def main(
    version: Optional[str] = typer.Argument(None),
    changelog_path: Path = typer.Argument(default_changelog_path),
) -> None:
    """Print the changes for the given version. By default, use the latest version (if any)."""
    with changelog_path.open(encoding="utf-8") as fp:
        md_ast = Document(fp)

    changelogs: dict[str, str] = {}
    current_version: Optional[str] = None

    for node in md_ast.children:
        if isinstance(node, block_token.Heading) and node.level == REVISION_HEADER_LEVEL:
            if (match := HEADER_REGEX.search(node.children[0].content)) is not None:
                _, revision = match.groups()
                current_version = revision
            else:
                current_version = None

        if current_version and isinstance(node, block_token.List):
            with Renderer() as renderer:
                changelogs[current_version] = renderer.render(node)

    if version is None and not changelogs:
        print("No version found in changelog.", file=sys.stderr)
        sys.exit(1)

    target_version = version if version is not None else sorted(changelogs)[-1]

    try:
        print(changelogs[target_version])
    except KeyError:
        print(f"Version {target_version} not found in changelog.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    typer.run(main)
