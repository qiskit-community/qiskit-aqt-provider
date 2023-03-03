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
example, running a Bell state:

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

## Arnica API

This version of the qiskit provider includes additional support for the Arnica API.

The implementation of the legacy API is still in place, so the existing Circuit API can
also be used as before.


### Sending circuits to Arnica:

1. Log into Arnica at https://aqt-portal-dev.firebaseapp.com
2. Choose a workspace
3. Copy your **Personal access token**
4. Run the following script:

```python
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit import QuantumCircuit, transpile

# If no `access_token` is passed to the constructor it is read from
# the AQT_TOKEN environment variable
provider = AQTProvider()

# The workspaces method returns a list of available workspaces and resources.
print(provider.workspaces())
```

This prints a table with all the workspaces that are accessible for this user:

```text
╒════════════════╤════════════════════╤═════════════════╤═════════════════╕
│ Workspace ID   │ Resource ID        │ Description     │ Resource type   │
╞════════════════╪════════════════════╪═════════════════╪═════════════════╡
│ default        │ simulator_noise    │ Noisy Simulator │ simulator       │
├────────────────┼────────────────────┼─────────────────┼─────────────────┤
│                │ simulator_no_noise │ Ideal Simulator │ simulator       │
├────────────────┼────────────────────┼─────────────────┼─────────────────┤
│ aqt            │ simulator_noise    │ Noisy Simulator │ simulator       │
├────────────────┼────────────────────┼─────────────────┼─────────────────┤
│                │ simulator_no_noise │ Ideal Simulator │ simulator       │
├────────────────┼────────────────────┼─────────────────┼─────────────────┤
│                │ ibex               │ Ibex            │ device          │
├────────────────┼────────────────────┼─────────────────┼─────────────────┤
│                │ pine               │ Pine            │ device          │
╘════════════════╧════════════════════╧═════════════════╧═════════════════╛
```

Select a workspace and resource from the output of the previous command:

```python
# Retrieve a backend by providing a `workspace` and `device_id`
backend = provider.get_resource("default", "simulator_noise")

# Creating and running a circuit works as before:
qc = QuantumCircuit(4, 4)
qc.h(0)
qc.cx(0, 1)
qc.cx(0, 2)
qc.cx(0, 3)
qc.measure([0, 1, 2, 3], [0, 1, 2, 3])
trans_qc = transpile(qc, backend, optimization_level=3)
job = backend.run(trans_qc)
print(job.result().get_counts())
```

### Setting portal URL

The url of the Arnica portal can be set with the `AQT_PORTAL_URL` environment variable.
Useful values could be:

```bash
# Local mini portal
PORTAL_URL = "http://localhost:7777"

# Local Arnica
PORTAL_URL = "http://localhost:5001/aqt-portal-dev/europe-west3"

# Deployed Arnica (Internal)
PORTAL_URL = "http://arnica.internal.aqt.eu:7777"

# Deployed Arnica (Firebase)
PORTAL_URL = "https://europe-west3-aqt-portal-dev.cloudfunctions.net"

```

## License

[Apache License 2.0].

[AQT]: https://www.aqt.eu/
[Apache License 2.0]: https://github.com/qiskit-community/qiskit-aqt-provider/blob/master/LICENSE.txt
