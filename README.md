# Qiskit AQT Provider

[![License](https://img.shields.io/github/license/Qiskit-Partners/qiskit-aqt-provider.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)
![Build Status](https://github.com/Qiskit-Partners/qiskit-aqt-provider/actions/workflows/main.yml/badge.svg?branch=master)
[![](https://img.shields.io/github/release/Qiskit-Partners/qiskit-aqt-provider.svg?style=popout-square)](https://github.com/Qiskit-Partners/qiskit-aqt-provider/releases)
[![](https://img.shields.io/pypi/dm/qiskit-aqt-provider.svg?style=popout-square)](https://pypi.org/project/qiskit-aqt-provider/)

**Qiskit** is an open-source SDK for working with quantum computers at the level of circuits, algorithms, and application modules.


This project contains a provider that allows access to **[AQT]** ion-trap quantum
system.

## Installation

You can install the provider using pip tool:

```bash
pip install qiskit-aqt-provider
```

`pip` will handle installing all the python dependencies automatically and you
will always install the  latest (and well-tested) version.

## Setting up the AQT Provider

Once the package is installed, you can use it to access the provider from
qiskit.

### Use your AQT credentials

You can initialize an AQT provider using your token locally with:

```python
from qiskit_aqt_provider import AQTProvider
aqt = AQTProvider('MY_TOKEN')
```

Where `MY_TOKEN` is your access token for the AQT device. Then you can access
the backends from that provider:

```python
print(aqt.backends())
backend = aqt.backends.aqt_qasm_simulator
```

You can then use that backend like you would use any other qiskit backend. For
example, running a bell state:

```python
from qiskit import QuantumCircuit, transpile
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0,1], [0,1])
trans_qc = transpile(qc, backend)
job = backend.run(trans_qc)
print(job.get_counts())
```

For running the quantum circuit on the ion-trap quantum device you need to use `aqt_innsbruck` as backend, which needs a different access token.

## License

[Apache License 2.0].

[AQT]: https://www.aqt.eu/
[Apache License 2.0]: https://github.com/qiskit-community/qiskit-aqt-provider/blob/master/LICENSE.txt
