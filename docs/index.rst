###########################################
Qiskit AQT provider |release| documentation
###########################################

The Qiskit AQT package provides access to `AQT <https://www.aqt.eu/>`__ systems
for Qiskit. It enables users to target and run circuits on AQT's simulators and
hardware.

.. _quick-start:

Quick start
-----------

Install the latest release from the `PyPI <https://pypi.org/project/qiskit-aqt-provider>`_:

.. code-block:: bash

  pip install qiskit-aqt-provider

.. warning:: Some dependencies might be pinned or tightly constrained to ensure optimal performance. If you encounter conflicts for your use case, please `open an issue <https://github.com/qiskit-community/qiskit-aqt-provider/issues/new/choose>`_.

Define a circuit that generates 2-qubit Bell state and sample it on a simulator backend running on the local machine:

.. code-block:: python

  from qiskit import QuantumCircuit

  from qiskit_aqt_provider import AQTProvider
  from qiskit_aqt_provider.primitives import AQTSampler

  # Define a circuit.
  circuit = QuantumCircuit(2)
  circuit.h(0)
  circuit.cx(0, 1)
  circuit.measure_all()

  # Select an execution backend.
  provider = AQTProvider()
  ideal_simulator = provider.offline.ideal()

  # Instantiate a sampler on the execution backend.
  sampler = AQTSampler(backend=ideal_simulator)

  # Sample the circuit on the execution backend.
  result = sampler.run(circuit).result()

  data = result.data[0]
  print(data.meas)

For more details see the :ref:`backends documentation <backends>`, the `examples <https://github.com/qiskit-community/qiskit-aqt-provider/tree/v2-migration/examples>`_, or the reference documentation.

.. toctree::
  :maxdepth: 2
  :hidden:

  Quick start <self>
  Circuit transpilation <transpilation>
  Backends <backends>
  Circuit evaluation <evaluation>
  Migrating to 2.0 <migrating>

.. toctree::
  :maxdepth: 1
  :caption: Reference
  :hidden:

  Provider <apidoc/provider>

  Cloud Access <apidoc/cloud>
  Direct Access <apidoc/direct>
  Offline Simulators <apidoc/offline>
  Transpiler plugin <apidoc/transpiler_plugin>
  Options <apidoc/options>
  Exceptions <apidoc/exceptions>
  Qiskit primitives <apidoc/primitives>
  

.. toctree::
  :hidden:
  :caption: External links

  Repository <https://github.com/qiskit-community/qiskit-aqt-provider>
  AQT <https://www.aqt.eu/products/arnica>
  Arnica API reference <https://arnica.aqt.eu/api/v1/docs>
