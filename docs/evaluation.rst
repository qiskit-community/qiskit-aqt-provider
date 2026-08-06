.. _evaluation:


==========================
Quantum circuit evaluation
==========================

Single circuit evaluation
-------------------------

Basic quantum circuit execution follows the regular Qiskit workflow. A quantum circuit is defined by a :class:`QuantumCircuit <qiskit.circuit.QuantumCircuit>` instance:

.. _bell-state-circuit:

.. code-block:: python

   circuit = qiskit.QuantumCircuit(2)
   circuit.h(0)
   circuit.cx(0, 1)
   circuit.measure_all()

.. warning:: AQT backends currently require a single projective measurement as last operation in a circuit. The hardware implementation always targets all the qubits in the quantum register, even if the circuit defines a partial measurement.

Prior to execution circuits must be transpiled to only use gates supported by the selected backend. The transpiler's entry point is the :func:`qiskit.transpile <qiskit.compiler.transpile>` function. See :ref:`Quantum circuit transpilation <transpilation>` for more information.

The :code:`run` method of all AQT backends submits the circuit for execution on a backend and immediately returns the corresponding job handle:

.. code-block:: python

   transpiled_circuit = qiskit.transpile(circuit, backend)
   job = backend.run(transpiled_circuit)

Each type of resource (cloud, direct access, or offline simulator) has a corresponding job class, all of which implement the :class:`JobV1 <qiskit.providers.JobV1>` interface. The returned job handle can be used to monitor the execution and retrieve results once the job completes.

The :code:`result` method blocks until the job completes, whether successfully or not. The return type is a standard Qiskit :class:`Result <qiskit.result.Result>` instance:

.. code-block:: python

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

Multiple options can be passed to :code:`run` that influence the backend behavior. See the reference documentation of the :class:`ResourceRunOptions <qiskit_aqt_provider.options.ResourceRunOptions>` class for a complete list.

Batch circuits evaluation
-------------------------

The resource's :code:`run` method can also be given a list of quantum circuits to execute as a batch. The returned :class:`JobV1 <qiskit.providers.JobV1>` is a handle for all the circuit executions.

.. note::
   Displaying job progress with a progress bar - as was possible in the v1 provider - is not (yet) supported by the v2 provider.

The result of a batch job is also a standard Qiskit :class:`Result <qiskit.result.Result>` instance. The `success` marker is true if and only if all individual circuits were successfully executed:

.. code-block:: python

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

.. attention:: In a batch job, the execution order of circuits is not guaranteed. In the :class:`Result <qiskit.result.Result>` instance, however, results are listed in submission order.

Job handle persistence
----------------------

.. important::
   Job persistence is not currently supported by the v2 provider.



Using Qiskit primitives
-----------------------

Circuit evaluation can also be performed using :mod:`Qiskit primitives <qiskit.primitives>` through their specialized implementations for AQT backends :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` and :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>`. These classes expose the :class:`BaseSamplerV2 <qiskit.primitives.BaseSamplerV2>` and :class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` interfaces respectively.

.. warning:: The generic implementations :class:`BackendSamplerV2 <qiskit.primitives.BackendSamplerV2>` and :class:`BackendEstimatorV2 <qiskit.primitives.BackendEstimatorV2>` are **not** compatible with backends retrieved from the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>`. Please use the specialized implementations :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` and :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>` instead.

For example, the :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` can evaluate bitstring quasi-probabilities for a given circuit. Using the :ref:`Bell state circuit <bell-state-circuit>` defined above, we see that the states :math:`|00\rangle` and :math:`|11\rangle` roughly have the same quasi-probability:

.. jupyter-execute::
   :hide-code:
   
   from qiskit.circuit import QuantumCircuit
   from qiskit_aqt_provider import AQTProvider

   provider = AQTProvider()
   backend = provider.offline.ideal()

   circuit = QuantumCircuit(2)
   circuit.h(0)
   circuit.cx(0, 1)
   circuit.measure_all()

.. jupyter-execute::

   from qiskit.visualization import plot_distribution
   from qiskit_aqt_provider.primitives import AQTSampler

   sampler = AQTSampler(backend=backend)
   result = sampler.run([circuit], shots=200).result()
   counts = result[0].data.meas.get_counts()
   plot_distribution(counts, figsize=(5, 4), color="#d1e0e0")


In this Bell state, the expectation value of the :math:`\sigma_z\otimes\sigma_z` operator is :math:`1`. This expectation value can be evaluated by applying the :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>`:

.. jupyter-execute::

   from qiskit.quantum_info import SparsePauliOp
   from qiskit_aqt_provider.primitives import AQTEstimator

   estimator = AQTEstimator(backend=backend)

   bell_circuit = QuantumCircuit(2)
   bell_circuit.h(0)
   bell_circuit.cx(0, 1)

   observable = SparsePauliOp.from_list([("ZZ", 1)])
   result = estimator.run([(bell_circuit, observable)], precision=0.1).result()
   print(result[0].data.evs)

.. tip:: The circuit passed to estimator's :meth:`run <qiskit.primitives.BaseEstimatorV2.run>` method is used to prepare the state the observable is evaluated in. Therefore, it must not contain unconditional measurement operations.
