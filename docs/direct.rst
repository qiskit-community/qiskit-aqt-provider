.. _direct:

==========
User guide
==========

This guide covers usage of the Qiskit AQT provider package with direct-access computing resources.

.. _direct-usage:
Usage
==============

The recommended way to use the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class to access resources directly is as a context manager. This will ensure that connections are properly cleaned up when leaving the context.

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider

   with AQTProvider() as provider:
      direct_access = provider.direct_access()
      backend = direct_access.get_resource("http://URL", "MY_ACCESS_TOKEN")
      ...


Contact your local system administrator to determine the exact base URL and access token to access your local quantum computing system.

Quantum register size
=====================

The number of qubits available on a given resource may vary. This is because the number of ions loaded in an AQT quantum computing resource is adjustable. All-to-all connectivity is always guaranteed, independently of the number of available qubits.

The number of qubits available for direct-access resources cannot be configured with this provider. 


.. warning:: The number of qubits is fetched from the resource when initializing the resource handle, i.e. when calling :meth:`get_resource <qiskit_aqt_provider._direct.provider.DirectAccessProvider.get_resource>`. Subsequent transpilation calls will assume that at least this number of qubits is available.
