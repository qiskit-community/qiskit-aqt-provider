# Qiskit AQT Provider

[![License](https://img.shields.io/github/license/Qiskit/qiskit-aqt-provider.svg?style=popout-square)](https://opensource.org/licenses/Apache-2.0)[![Build Status](https://img.shields.io/travis/com/Qiskit/qiskit-aqt-provider/master.svg?style=popout-square)](https://travis-ci.com/Qiskit/qiskit-aqt-provider)[![](https://img.shields.io/github/release/Qiskit/qiskit-aqt-provider.svg?style=popout-square)](https://github.com/Qiskit/qiskit-aqt-provider/releases)[![](https://img.shields.io/pypi/dm/qiskit-aqt-provider.svg?style=popout-square)](https://pypi.org/project/qiskit-aqt-provider/)

Qiskit is an open-source framework for working with noisy intermediate-scale
quantum computers (NISQ) at the level of pulses, circuits, and algorithms.

This project contains a provider that allows access to **[AQT]** ion-trap quantum
devices.

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
from qiskit.providers.aqt import AQT
aqt = AQT.enable_account('MY_TOKEN')
```

Where `MY_TOKEN` is your access token for the AQT device. Then you can access
the backends from that provider:

```python
print(aqt.backends())
backend = aqt.get_backend('aqt_qasm_simulator')
```

You can then use that backend like you would use any other qiskit backend. For
example, running a bell state:

```python
from qiskit import *
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0,1], [0,1])
result = execute(qc, backend, shots=100).result()
print(result.get_counts(qc))
```

For running the quantum circuit on the ion-trap quantum device you need to use `aqt_innsbruck` as backend, which needs a different access token.

## Authors and Citation

The Qiskit AQT provider is the work of many people who contribute to the
project at different levels. If you use Qiskit, please cite as per the included
[BibTeX file].

## License

[Apache License 2.0].

[AQT]: https://www.aqt.eu/
[BibTeX file]: https://github.com/Qiskit/qiskit/blob/master/Qiskit.bib
[Apache License 2.0]: https://github.com/Qiskit/qiskit-aqt-provider/blob/master/LICENSE.txt
