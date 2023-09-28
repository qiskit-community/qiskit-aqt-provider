.. _user-guide:

==========
User guide
==========

This guide covers usage of the Qiskit AQT provider package with the AQT cloud portal beyond the :ref:`quick start <quick-start>` example.

.. jupyter-execute::
    :hide-code:

    import qiskit
    from math import pi

Provider configuration
======================

The primary interface to the AQT cloud portal exposed by this package is the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class. Instances of it are able to authenticate to the AQT cloud with an access token, list available resources, and retrieve handles to resources for executing quantum circuits jobs.

.. tip:: If no access token to the AQT cloud is available, the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` can nevertheless provide access to AQT-compatible simulators running on the local machine. This is the default behavior if the ``access_token`` argument to :meth:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider.__init__>` is empty or invalid.

The access token can be configured by passing it as the first argument to the
:class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` initializer:

.. jupyter-execute::

   from qiskit_aqt_provider import AQTProvider

   provider = AQTProvider("ACCESS_TOKEN")

Alternatively, the access token can be provided by the environment variable ``AQT_TOKEN``. By default, the local execution environment is augmented by assignments in a local ``.env`` file, e.g.

.. code-block::

   AQT_TOKEN=ACCESS_TOKEN

Loading a local environment override file can be controlled by further arguments to :meth:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider.__init__>`.

Available backends
==================

A configured provider can be used to list available quantum computing backends.

Each backend is identified by a *workspace* it belongs to, and a unique *resource* identifier within that workspace. The *resource type* helps distinguishing between real hardware (``device``), hosted simulators (``simulator``) and offline simulators (``offline_simulator``).

The :meth:`AQTProvider.backends <qiskit_aqt_provider.aqt_provider.AQTProvider.backends>` method returns a pretty-printable collection of available backends and their associated metadata:

.. _available-backends:

.. jupyter-execute::

    print(provider.backends())

.. hint:: The exact list of available backends depends on the authorizations carried by the configured access token. In this guide, an invalid token is used and the only available backends are simulators running on the local machine.

Backend selection
=================

Backends are selected by passing criteria that uniquely identify a backend within the available backends to the :meth:`AQTProvider.get_backend <qiskit_aqt_provider.aqt_provider.AQTProvider.get_backend>` method.

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

Quantum circuit evaluation
==========================

Single circuit evaluation
-------------------------

Basic quantum circuit execution follows the regular Qiskit workflow. A quantum circuit is defined by a :class:`QuantumCircuit <qiskit.circuit.QuantumCircuit>` instance:

.. jupyter-execute::

   circuit = qiskit.QuantumCircuit(2)
   circuit.h(0)
   circuit.cnot(0, 1)
   circuit.measure_all()

.. warning:: AQT backends currently require a single projective measurement as last operation in a circuit. The hardware implementation always targets all the qubits in the quantum register, even if the circuit defines a partial measurement.

The :func:`qiskit.execute <qiskit.execute_function.execute>` schedules the circuit for execution on a backend and immediately returns the corresponding job handle:

.. jupyter-execute::

   job = qiskit.execute(circuit, backend)

The :meth:`AQTJob.result <qiskit_aqt_provider.aqt_job.AQTJob.result>` method blocks until the job completes (either successfully or not). The return type is a standard Qiskit :class:`Result <qiskit.result.Result>` instance:

.. jupyter-execute::

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

Multiple options can be passed to :func:`qiskit.execute <qiskit.execute_function.execute>` that influence the backend behavior and interaction with the AQT cloud. See the reference documentation of the :class:`AQTOptions <qiskit_aqt_provider.aqt_options.AQTOptions>` class for a complete list.

Batch circuits evaluation
-------------------------

The :func:`qiskit.execute <qiskit.execute_function.execute>` function can also be given a list of quantum circuits to execute as a batch. The returned :class:`AQTJob <qiskit_aqt_provider.aqt_job.AQTJob>` is a handle for all the circuit executions. Execution of individual circuits within such a batch job can be monitored using the :meth:`AQTJob.progress <qiskit_aqt_provider.aqt_job.AQTJob.progress>` method. The :attr:`with_progress_bar <qiskit_aqt_provider.aqt_options.AQTOptions.with_progress_bar>` option on AQT backends (enabled by default) allows printing an interactive progress bar on the standard error stream (:data:`sys.stderr`).

.. jupyter-execute::

   job = qiskit.execute([circuit, circuit], backend)
   print(job.progress())

The result of a batch job is also a standard Qiskit :class:`Result <qiskit.result.Result>` instance. The `success` marker is true if and only if all individual circuits were successfully executed:

.. jupyter-execute::

   result = job.result()

   if result.success:
       print(result.get_counts())
   else:
       raise RuntimeError

.. warning:: In a batch job, the execution order of circuits is not guaranteed. In the :class:`Result <qiskit.result.Result>` instance, however, results are listed in submission order.

Quantum circuit transpilation
=============================

AQT backends only natively implement a limited but complete set of quantum gates. The Qiskit transpiler allows transforming any non-conditional quantum circuit to use only supported quantum gates. The set of supported gates is defined in the transpiler :class:`Target <qiskit.transpiler.Target>` used by the AQT backends:

.. _basis-gates:

.. jupyter-execute::

   print(list(backend.target.operation_names))

.. warning:: For implementation reasons, the transpilation target declares :class:`RXGate <qiskit.circuit.library.RXGate>` as basis gate. The AQT API, however, only accepts the more general :class:`RGate <qiskit.circuit.library.RGate>`, in addition to :class:`RZGate <qiskit.circuit.library.RZGate>`, the entangling :class:`RXXGate <qiskit.circuit.library.RXXGate>`, and the :class:`Measure <qiskit.circuit.library.Measure>` operation.

Circuit transpilation targeting the AQT backends is automatically performed when using the :func:`qiskit.execute <qiskit.execute_function.execute>` function. The optimization level can be tuned using the ``optimization_level=0,1,2,3`` argument.

Transpilation can also be triggered separately from job submission using the :func:`qiskit.transpile <qiskit.compiler.transpile>` function, allowing to inspect the transformation from the original circuit:

.. jupyter-execute::
   :hide-code:

   circuit.draw("mpl")

to the transpiled one:

.. jupyter-execute::

   transpiled_circuit = qiskit.transpile(circuit, backend, optimization_level=2)
   transpiled_circuit.draw("mpl")


Transpiler bypass
-----------------

.. warning:: We highly recommend to always use the built-in transpiler, at least with ``optimization_level=0``. This guarantees that the quantum circuit is valid for submission to the AQT cloud. In particular, it wraps the gate parameters to fit in the restricted ranges accepted by the `AQT API <https://arnica-stage.aqt.eu/api/v1/docs>`_. In addition, higher optimization levels may significantly improve the circuit execution speed.

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

Transpiler plugin
-----------------

The built-in transpiler largely leverages the :mod:`qiskit.transpiler`. Custom passes are registered in addition to the presets, irrespective of the optimization level, to ensure that the transpiled circuit is compatible with the restricted parameter ranges accepted by the `AQT API <https://arnica-stage.aqt.eu/api/v1/docs>`_:

* in the translation stage, the :class:`WrapRxxAngles <qiskit_aqt_provider.transpiler_plugin.WrapRxxAngles>` pass exploits the periodicity of the :class:`RXXGate <qiskit.circuit.library.RXXGate>` to wrap its angle :math:`\theta` to the :math:`[0,\,\pi/2]` range. This may come at the expense of extra single-qubit rotations.
* in the scheduling stage, the :class:`RewriteRxAsR <qiskit_aqt_provider.transpiler_plugin.RewriteRxAsR>` pass rewrites :class:`RXGate <qiskit.circuit.library.RXGate>` operations as :class:`RGate <qiskit.circuit.library.RGate>` and wraps the angles :math:`\theta\in[0,\,\pi]` and :math:`\phi\in[0,\,2\pi]`. This does not restrict the generality of quantum circuits and enables efficient native implementations.

.. warning:: Circuits accepted by the AQT API are executed after applying one further transformation. Small-angle :math:`\theta` instances of :class:`RGate <qiskit.circuit.library.RGate>` are substituted as

  :math:`R(\theta,\,\phi)\ \to\  R(\pi, \pi)\cdot R(\theta+\pi,\,\phi)`.

  The threshold for triggering this transformation is an implementation detail, typically around :math:`\theta=\pi/5`. Please contact AQT for details.
