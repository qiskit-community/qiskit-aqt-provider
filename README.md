# Qiskit AQT Provider

[![Latest release](https://img.shields.io/pypi/v/qiskit-aqt-provider-rc.svg)](https://pypi.python.org/pypi/qiskit-aqt-provider-rc)
[![License](https://img.shields.io/pypi/l/qiskit-aqt-provider-rc.svg)](https://pypi.python.org/pypi/qiskit-aqt-provider-rc)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/qiskit-aqt-provider-rc.svg)](https://pypi.python.org/pypi/qiskit-aqt-provider-rc)
![Build Status](https://github.com/alpine-quantum-technologies/qiskit-aqt-provider-rc/actions/workflows/poetry.yml/badge.svg?branch=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

[Qiskit](https://qiskit.org/) is an open-source SDK for working with quantum computers at the level of circuits, algorithms, and application modules.

This project contains a provider that allows access to [AQT](https://www.aqt.eu/) ion-trap quantum computing
systems.

## Installation

We encourage installing released packages using the [`pip`](https://pip.pypa.io/en/stable/) tool:

```
pip install [--update] qiskit-aqt-provider-rc
```

Please note that this command should always be executed in a vanilla virtual environment, such that dependencies correctly respect the bounds set in the [pyproject.toml](https://github.com/alpine-quantum-technologies/qiskit-aqt-provider-internal/blob/master/pyproject.toml) file.

## Usage

See the [user guide](https://github.com/alpine-quantum-technologies/qiskit-aqt-provider-internal/blob/master/docs/guide.rst) and the [examples](https://github.com/alpine-quantum-technologies/qiskit-aqt-provider-internal/tree/master/examples).
