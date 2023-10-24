###########################################
Qiskit AQT provider |version| documentation
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

.. jupyter-execute::

   from qiskit import QuantumCircuit

   from qiskit_aqt_provider import AQTProvider
   from qiskit_aqt_provider.primitives import AQTSampler

   # Define a circuit.
   circuit = QuantumCircuit(2)
   circuit.h(0)
   circuit.cx(0, 1)
   circuit.measure_all()

   # Select an execution backend.
   # Any token (even invalid) gives access to the offline simulation backends.
   provider = AQTProvider("ACCESS_TOKEN")
   backend = provider.get_backend("offline_simulator_no_noise")

   # Instantiate a sampler on the execution backend.
   sampler = AQTSampler(backend)

   # Sample the circuit on the execution backend.
   result = sampler.run(circuit).result()

   quasi_dist = result.quasi_dists[0]
   print(quasi_dist)

For more details see the :ref:`user guide <user-guide>`, a selection of `examples <https://github.com/qiskit-community/qiskit-aqt-provider/tree/master/examples>`_, or the reference documentation.

.. toctree::
  :maxdepth: 1
  :hidden:

  Quick start <self>
  User guide <guide>

.. toctree::
  :maxdepth: 1
  :caption: Reference
  :hidden:

  AQTProvider <apidoc/provider>
  AQTResource <apidoc/resource>
  AQTJob <apidoc/job>
  AQTOptions <apidoc/options>
  Qiskit primitives <apidoc/primitives>
  Transpiler plugin <apidoc/transpiler_plugin>

.. toctree::
  :hidden:
  :caption: External links

  Repository <https://github.com/qiskit-community/qiskit-aqt-provider>
  AQT <https://www.aqt.eu/qc-systems>
  API reference <https://arnica-stage.aqt.eu/api/v1/docs>
