===========
Users guide
===========

.. jupyter-execute::
    :hide-code:

    from qiskit import *

Setting up the provider
=======================

To begin, the `AQTProvider` must be instantiated with
an AQT access token:

.. jupyter-execute::

    from qiskit_aqt_provider import AQTProvider

    aqt = AQTProvider('MY_TOKEN')

Once loaded with your credentials, the provider
gives access to the available AQT backend. These
backends can be listed using

.. jupyter-execute::

    print(aqt.backends())

and selected using autocomplete

.. jupyter-execute::

    backend = aqt.backends.aqt_qasm_simulator

One can also query a specific backend by name:

.. jupyter-execute::

    backend = aqt.get_backend('aqt_qasm_simulator')


Compiling circuits for AQT backends
===================================

Although one may right a quantum circuit using any
selection of quantum gates, the AQT backends can only
run a subset of these operations.  The gates a given
backend supports can be found from the configuration
information:

.. jupyter-execute::

    backend.configuration().basis_gates

Unless written in terms of this basis set, a circuit
destined for a AQT backend must first be transpiled
into the required gates.  For example:

.. jupyter-execute::

    qc = QuantumCircuit(5, 4)
    qc.x(4)
    qc.h(range(5))
    qc.barrier()
    qc.cx([0,1,3], [4,4,4])
    qc.barrier()
    qc.h(range(4))
    qc.measure(range(4), range(4))
    qc.draw('mpl')

can be decomposed into the target gate set via:

.. jupyter-execute::

    trans_qc = transpile(qc, backend)
    trans_qc.draw('mpl')



Executing circuits
==================

A circuit can be passed to the backend using the `run()`
method to retrieve a job:

.. code-block:: python3

    job = backend.run(trans_qc)


A circuit can also be sent to a backend using the
Qiskit `execute` function:

.. code-block:: python3

    job = execute(trans_qc, backend)
