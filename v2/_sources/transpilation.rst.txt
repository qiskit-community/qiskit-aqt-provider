.. _transpilation:

.. jupyter-execute::
   :hide-code:

   from math import pi
   
   import qiskit
   from qiskit_aqt_provider import AQTProvider

   provider = AQTProvider()
   backend = provider.offline.ideal()

   circuit = qiskit.QuantumCircuit(2)
   circuit.h(0)
   circuit.cx(0, 1)
   circuit.measure_all()


=============================
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
   :hide-code:

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
* in the scheduling stage, single-qubit gates runs are decomposed as ZXZ products using Qiskit's :class:`OneQubitEulerDecompose <qiskit.synthesis.OneQubitEulerDecomposer>`, taking advantage of the virtual nature of the Z gate on AQT's architecture. The :class:`RewriteRxAsR <qiskit_aqt_provider.transpiler_plugin.RewriteRxAsR>` pass subsequently rewrites :class:`RXGate <qiskit.circuit.library.RXGate>` operations as :class:`RGate <qiskit.circuit.library.RGate>`, wrapping the angle arguments to :math:`\theta\in[0,\,\pi]` and :math:`\phi\in[0,\,2\pi]`) in order to satisfy the AQT API constraints.

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

.. code-block:: python

   from qiskit import QuantumCircuit

   qc = QuantumCircuit(2)
   qc.initialize("01")
   # ...
   qc.measure_all()

is equivalent to:

.. code-block:: python

   from qiskit import QuantumCircuit

   qc = QuantumCircuit(2)
   qc.prepare_state("01")
   # ...
   qc.measure_all()
