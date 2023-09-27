###########################################
Qiskit AQT provider |version| documentation
###########################################

The Qiskit AQT package provides access to `AQT <https://www.aqt.eu/>`__ systems
for Qiskit. It enables users to target and run circuits on AQT's simulators and
hardware.

.. _quick-start:

Quick start
-----------

Define a circuit that generates 2-qubit Bell state and execute it on a simulator backend:

.. jupyter-execute::

   import qiskit
   from qiskit import QuantumCircuit
   from qiskit_aqt_provider import AQTProvider

   backend = AQTProvider("ACCESS_TOKEN").get_backend("offline_simulator_no_noise")

   qc = QuantumCircuit(2)
   qc.h(0)
   qc.cnot(0, 1)
   qc.measure_all()

   result = qiskit.execute(qc, backend, with_progress_bar=False).result()
   print(result.get_counts())


For more details see the :ref:`user guide <user-guide>`, a selection of `examples <https://github.com/qiskit-community/qiskit-aqt-provider/tree/master/examples>`_, or the API reference.

.. toctree::
  :maxdepth: 1
  :hidden:

  Quick start <self>
  User guide <guide>

.. toctree::
  :maxdepth: 1
  :caption: API Reference
  :hidden:

  AQTProvider <apidoc/provider>
  AQTResource <apidoc/resource>
  AQTJob <apidoc/job>
  AQTOptions <apidoc/options>
  Transpiler plugin <apidoc/transpiler_plugin>
