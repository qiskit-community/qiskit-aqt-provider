"""Extract the coverage target from the pyproject.toml file.

This is used by the Github workflows to write the coverage report comment on PRs."""

import tomlkit

if __name__ == "__main__":
    with open("pyproject.toml") as fp:
        data = tomlkit.load(fp)
        print(float(data["tool"]["coverage"]["report"]["fail_under"]) / 100.0)  # type: ignore[index, arg-type]
