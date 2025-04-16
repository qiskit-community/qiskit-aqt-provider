.. _user-guide:

==========
User guide
==========

This guide covers usage of the Qiskit AQT provider package with the AQT cloud portal and direct-access computing resources beyond the :ref:`quick start <quick-start>` example.

.. jupyter-execute::
    :hide-code:

    import qiskit
    from math import pi

Provider configuration
======================

Handles to computing resources are obtained through the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class. For remote resources, it also handles authentication to the AQT cloud and listing of available resources.

.. tip:: If no access token to the AQT cloud is available, the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` can nevertheless provide handles to direct-access resources and AQT-compatible simulators running on the local machine. This is the default behavior if the ``access_token`` argument to :meth:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider.__init__>` is empty or invalid.

The access token can be configured by passing it as the first argument to the
:class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` initializer:

.. jupyter-execute::

   from qiskit_aqt_provider import AQTProvider

   provider = AQTProvider("ACCESS_TOKEN")

Alternatively, the access token can be provided by the environment variable ``AQT_TOKEN``. By default, the local execution environment is augmented by assignments in a local ``.env`` file, e.g.

.. code-block::

   AQT_TOKEN=ACCESS_TOKEN

Loading a local environment override file can be controlled by further arguments to :meth:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider.__init__>`.

Listing remote and simulator resources
======================================

A configured provider can be used to list available remote and local simulator quantum computing backends.

Each backend is identified by a *workspace* it belongs to, and a unique *resource* identifier within that workspace. The *resource type* helps distinguishing between real hardware (``device``), hosted simulators (``simulator``) and offline simulators (``offline_simulator``).

The :meth:`AQTProvider.backends <qiskit_aqt_provider.aqt_provider.AQTProvider.backends>` method returns a pretty-printable collection of available backends and their associated metadata:

.. _available-backends:

.. jupyter-execute::

    print(provider.backends())

.. hint:: The exact list of available backends depends on the authorizations carried by the configured access token. In this guide, an invalid token is used and the only available backends are simulators running on the local machine.

Remote backend selection
========================

Remote backends are selected by passing criteria that uniquely identify a backend within the available backends to the :meth:`AQTProvider.get_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_backend>` method.

The available filtering criteria are the resource identifier (``name``), the containing workspace (``workspace``), and the resource type (``backend_type``). Each criterion can be expressed as a string that must exactly match, or a regular expression pattern using the Python `syntax <https://docs.python.org/3/library/re.html#regular-expression-syntax>`_.

.. hint:: The resource ID filter is called ``name`` for compatibility reasons with the underlying Qiskit implementation.

The ``name`` filter is compulsory. If it is uniquely identifying a resource, it is also sufficient:

.. jupyter-execute::

    backend = provider.get_backend("offline_simulator_no_noise")

The same backend can be retrieved by specifying all filters (see the list of :ref:`available backends <available-backends>` for this guide):

.. jupyter-execute::

   same_backend = provider.get_backend("offline_simulator_no_noise", workspace="default", backend_type="offline_simulator")

If the filtering criteria correspond to multiple or no backends, a :class:`QiskitBackendNotFoundError <qiskit.providers.QiskitBackendNotFoundError>` exception is raised.

.. jupyter-execute::
   :hide-code:

   backend.options.with_progress_bar = False
   backend.simulator.options.seed_simulator = 1000

Direct-access backends
======================

Direct-access resources handles are obtained from a provider using the :meth:`get_direct_access_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_direct_access_backend>` method:

.. jupyter-execute::

   direct_access_backend = provider.get_direct_access_backend("http://URL")

Contact your local system administrator to determine the exact base URL to access your local quantum computing system.

.. tip:: Resources handles returned by :meth:`get_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_backend>` and :meth:`get_direct_access_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_direct_access_backend>` both implement the Qiskit :class:`BackendV2 <qiskit.providers.BackendV2>` interface can be used exchangeably in the following examples.

Quantum circuit evaluation
==========================

Single circuit evaluation
-------------------------

Basic quantum circuit execution follows the regular Qiskit workflow. A quantum circuit is defined by a :class:`QuantumCircuit <qiskit.circuit.QuantumCircuit>` instance:

.. _bell-state-circuit:

.. jupyter-execute::

   circuit = qiskit.QuantumCircuit(2)
   circuit.h(0)
   circuit.cx(0, 1)
   circuit.measure_all()

.. warning:: AQT backends currently require a single projective measurement as last operation in a circuit. The hardware implementation always targets all the qubits in the quantum register, even if the circuit defines a partial measurement.

Prior to execution circuits must be transpiled to only use gates supported by the selected backend. The transpiler's entry point is the :func:`qiskit.transpile <qiskit.compiler.transpile>` function. See `Quantum circuit transpilation`_ for more information.
The :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>` method schedules the circuit for execution on a backend and immediately returns the corresponding job handle:

.. jupyter-execute::

   transpiled_circuit = qiskit.transpile(circuit, backend)
   job = backend.run(transpiled_circuit)

The :meth:`AQTJob.result <qiskit_aqt_provider.aqt_job.AQTJob.result>` method blocks until the job completes (either successfully or not). The return type is a standard Qiskit :class:`Result <qiskit.result.Result>` instance:

.. jupyter-execute::

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

Multiple options can be passed to :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>` that influence the backend behavior and interaction with the AQT cloud. See the reference documentation of the :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>` class for a complete list.

Batch circuits evaluation
-------------------------

The :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>` method can also be given a list of quantum circuits to execute as a batch. The returned :class:`AQTJob <qiskit_aqt_provider.aqt_job.AQTJob>` is a handle for all the circuit executions. Execution of individual circuits within such a batch job can be monitored using the :meth:`AQTJob.progress <qiskit_aqt_provider.aqt_job.AQTJob.progress>` method. The :attr:`with_progress_bar <qiskit_aqt_provider.aqt_options.AQTOptions.with_progress_bar>` option on AQT backends (enabled by default) allows printing an interactive progress bar on the standard error stream (:data:`sys.stderr`).

.. jupyter-execute::

   transpiled_circuit0, transpiled_circuit1 = qiskit.transpile([circuit, circuit], backend)
   job = backend.run([transpiled_circuit0, transpiled_circuit1])
   print(job.progress())

The result of a batch job is also a standard Qiskit :class:`Result <qiskit.result.Result>` instance. The `success` marker is true if and only if all individual circuits were successfully executed:

.. jupyter-execute::

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

.. warning:: In a batch job, the execution order of circuits is not guaranteed. In the :class:`Result <qiskit.result.Result>` instance, however, results are listed in submission order.

Job handle persistence
----------------------

Due to the limited availability of quantum computing resources, a job may have to wait a significant amount of time in the AQT cloud portal scheduling queues. To ease up writing resilient programs, job handles can be persisted to disk on the local machine and retrieved at a later point:

.. jupyter-execute::

   job_ids = set()

   job = backend.run(transpiled_circuit)
   job.persist()
   job_ids.add(job.job_id())

   print(job_ids)

   # possible interruptions of the program, including full shutdown of the local machine

   from qiskit_aqt_provider.aqt_job import AQTJob
   job_id, = job_ids
   restored_job = AQTJob.restore(job_id, access_token="ACCESS_TOKEN")
   print(restored_job.result().get_counts())

By default, persisted job handles can only be retrieved once, as the stored data is removed from the local storage upon retrieval. This ensures that the local storage does not grow unbounded in the common uses cases. This behavior can be altered by passing ``remove_from_store=False`` to :meth:`AQTJob.restore <qiskit_aqt_provider.aqt_job.AQTJob.restore>`.

.. warning:: Job handle persistence is also implemented for jobs running on offline simulators, which allows to seamlessly switch to such backends for testing purposes. However, since the state of the local simulator backend cannot be persisted, offline simulator jobs are re-submitted when restored, leading to the assignment of a new identifier and varying results.

Using Qiskit primitives
-----------------------

Circuit evaluation can also be performed using :mod:`Qiskit primitives <qiskit.primitives>` through their specialized implementations for AQT backends :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` and :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>`. These classes expose the :class:`BaseSamplerV1 <qiskit.primitives.BaseSamplerV1>` and :class:`BaseEstimatorV1 <qiskit.primitives.BaseEstimatorV1>` interfaces respectively.

.. warning:: The generic implementations :class:`BackendSampler <qiskit.primitives.BackendSampler>` and :class:`BackendEstimator <qiskit.primitives.BackendEstimator>` are **not** compatible with backends retrieved from the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>`. Please use the specialized implementations :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` and :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>` instead.

For example, the :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` can evaluate bitstring quasi-probabilities for a given circuit. Using the :ref:`Bell state circuit <bell-state-circuit>` defined above, we see that the states :math:`|00\rangle` and :math:`|11\rangle` roughly have the same quasi-probability:

.. jupyter-execute::

   from qiskit.visualization import plot_distribution
   from qiskit_aqt_provider.primitives import AQTSampler

   sampler = AQTSampler(backend)
   result = sampler.run(circuit, shots=200).result()
   data = {f"{b:02b}": p for b, p in result.quasi_dists[0].items()}
   plot_distribution(data, figsize=(5, 4), color="#d1e0e0")


In this Bell state, the expectation value of the the :math:`\sigma_z\otimes\sigma_z` operator is :math:`1`. This expectation value can be evaluated by applying the :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>`:

.. jupyter-execute::

   from qiskit.quantum_info import SparsePauliOp
   from qiskit_aqt_provider.primitives import AQTEstimator

   estimator = AQTEstimator(backend)

   bell_circuit = qiskit.QuantumCircuit(2)
   bell_circuit.h(0)
   bell_circuit.cx(0, 1)

   observable = SparsePauliOp.from_list([("ZZ", 1)])
   result = estimator.run(bell_circuit, observable).result()
   print(result.values[0])

.. tip:: The circuit passed to estimator's :meth:`run <qiskit.primitives.BaseEstimatorV1.run>` method is used to prepare the state the observable is evaluated in. Therefore, it must not contain unconditional measurement operations.

Quantum circuit transpilation
=============================

AQT backends only natively implement a limited but complete set of quantum gates. The Qiskit transpiler allows transforming any non-conditional quantum circuit to use only supported quantum gates. The set of supported gates is defined in the transpiler :class:`Target <qiskit.transpiler.Target>` used by the AQT backends:

.. _basis-gates:

.. jupyter-execute::

   print(list(backend.target.operation_names))

The transpiler's entry point is the :func:`qiskit.transpile <qiskit.compiler.transpile>` function. The optimization level can be tuned using the ``optimization_level=0,1,2,3`` argument. One can inspect how the circuit is converted from the original one:

.. jupyter-execute::
   :hide-code:

   circuit.draw("mpl", style="bw")

to the transpiled one:

.. jupyter-execute::

   transpiled_circuit = qiskit.transpile(circuit, backend, optimization_level=3)
   transpiled_circuit.draw("mpl", style="bw")

.. tip:: While all optimization levels produce circuits compatible with the AQT API, optimization level 3 typically produces circuits with the least number of gates, thus decreasing the circuit evaluation duration and mitigating errors.

Transpiler bypass
-----------------

.. warning:: We highly recommend to always use the built-in transpiler, at least with ``optimization_level=0``. This guarantees that the quantum circuit is valid for submission to the AQT cloud. In particular, it wraps the gate parameters to fit in the restricted ranges accepted by the `AQT API <https://arnica.aqt.eu/api/v1/docs>`_. In addition, higher optimization levels may significantly improve the circuit execution speed.

If a circuit is already defined in terms of the :ref:`native gates set <basis-gates>` with their restricted parameter ranges and no optimization is wanted, it can be submitted for execution without any additional transformation using the :meth:`AQTResource.run <qiskit_aqt_provider.aqt_resource.AQTResource.run>` method:

.. jupyter-execute::

   native_circuit = qiskit.QuantumCircuit(2)
   native_circuit.rxx(pi/2, 0, 1)
   native_circuit.r(pi, 0, 0)
   native_circuit.r(pi, pi, 1)
   native_circuit.measure_all()

   job = backend.run(native_circuit)
   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

Circuits that do not satisfy the AQT API restrictions are rejected by raising a :class:`ValueError` exception.

.. _transpiler-plugin:

Transpiler plugin
-----------------

The built-in transpiler largely leverages the :mod:`qiskit.transpiler`. Custom passes are registered in addition to the presets, irrespective of the optimization level, to ensure that the transpiled circuit is compatible with the restricted parameter ranges accepted by the `AQT API <https://arnica.aqt.eu/api/v1/docs>`_:

* in the translation stage, the :class:`WrapRxxAngles <qiskit_aqt_provider.transpiler_plugin.WrapRxxAngles>` pass exploits the periodicity of the :class:`RXXGate <qiskit.circuit.library.RXXGate>` to wrap its angle :math:`\theta` to the :math:`[0,\,\pi/2]` range. This may come at the expense of extra single-qubit rotations.
* in the scheduling stage, 1-qubit gates runs are decomposed as ZXZ products using Qiskit's :class:`OneQubitEulerDecompose <qiskit.synthesis.OneQubitEulerDecomposer>`, taking advantage of the virtual nature of the Z gate on AQT's architecture. The :class:`RewriteRxAsR <qiskit_aqt_provider.transpiler_plugin.RewriteRxAsR>` pass subsequently rewrites :class:`RXGate <qiskit.circuit.library.RXGate>` operations as :class:`RGate <qiskit.circuit.library.RGate>`, wrapping the angle arguments to :math:`\theta\in[0,\,\pi]` and :math:`\phi\in[0,\,2\pi]`) in order to satisfy the AQT API constraints.

.. tip:: AQT computing resources natively implement :class:`RXXGate <qiskit.circuit.library.RXXGate>` with :math:`\theta` continuously varying in :math:`(0,\,\pi/2]`. For optimal performance, the transpiler output should be inspected to make sure :class:`RXXGate <qiskit.circuit.library.RXXGate>` instances are not transpiled to unified angles (often :math:`\theta=\pi/2`).

Transpilation in Qiskit primitives
----------------------------------

The generic implementations of the Qiskit primitives :class:`Sampler <qiskit.primitives.BaseSamplerV1>` and :class:`Estimator <qiskit.primitives.BaseEstimatorV1>` cache transpilation results to improve their runtime performance. This is particularly effective when evaluating batches of circuits that differ only in their parametrization.

However, some passes registered by the AQT :ref:`transpiler plugin <transpiler-plugin>` require knowledge of the bound parameter values. The specialized implementations :class:`AQTSampler <qiskit_aqt_provider.primitives.sampler.AQTSampler>` and :class:`AQTEstimator <qiskit_aqt_provider.primitives.estimator.AQTEstimator>` use a hybrid approach, where the transpilation results of passes that do not require bound parameters are cached, while the small subset of passes that require fixed parameter values is executed before each circuit submission to the execution backend.

Circuit modifications behind the remote API
-------------------------------------------

Circuits accepted by the AQT API are executed exactly as they were transmitted, with the only exception that small-angle :math:`\theta` instances of :class:`RGate <qiskit.circuit.library.RGate>` are substituted with

  :math:`R(\theta,\,\phi)\ \to\  R(\pi, \pi)\cdot R(\theta+\pi,\,\phi)`.

The threshold for triggering this transformation is an implementation detail, typically around :math:`\theta=\pi/5`. Please contact AQT for details.

Common limitations
==================

Reset operations are not supported
----------------------------------

Because AQT backends do not support in-circuit state reinitialization of specific qubits, the :class:`Reset <qiskit.circuit.reset.Reset>` operation is not supported. The Qiskit transpiler will fail synthesis for circuits using it (e.g. through :meth:`QuantumCircuit.initialize <qiskit.circuit.QuantumCircuit.initialize>`) when targeting AQT backends.

AQT backends always prepare the quantum register in the :math:`|0\rangle\otimes\cdots\otimes|0\rangle` state. Thus, :meth:`QuantumCircuit.prepare_state <qiskit.circuit.QuantumCircuit.prepare_state>` is an alternative to :meth:`QuantumCircuit.initialize <qiskit.circuit.QuantumCircuit.initialize>` as first instruction in the circuit:

.. jupyter-execute::

   from qiskit import QuantumCircuit

   qc = QuantumCircuit(2)
   qc.initialize("01")
   # ...
   qc.measure_all()

is equivalent to:

.. jupyter-execute::

   from qiskit import QuantumCircuit

   qc = QuantumCircuit(2)
   qc.prepare_state("01")
   # ...
   qc.measure_all()
