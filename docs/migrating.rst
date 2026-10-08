################
Migrating to 2.0
################

Providers
---------

The AQT provider now exposes individual providers for each kind of AQT backend (cloud, direct access, and offline simulator). The main :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class is now only a factory for these individual providers. For example, instead of:

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider
   provider = AQTProvider()
   backend = provider.backend("simulator_no_noise")


You should now do:

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider
   provider = AQTProvider()
   backend = provider.offline.ideal()

Check the :ref:`backends documentation <backends>` for more details on how to access a particular AQT resource with the v2 provider.


Context manager for remote backends
-----------------------------------

The AQTProvider should now be used as a context manager when working with remote backends (cloud and direct access). This ensures that network connections are properly closed after use. For example, instead of:

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider
   provider = AQTProvider()
   backend = provider.get_backend("simulator_no_noise", workspace="aqt_simulators")
   # use backend
   # ...


You should now do:

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider

   with AQTProvider() as provider:
       backend = provider.cloud().fetch_workspaces().get_by_id("aqt_simulators").get_backend("simulator_no_noise")
       # use backend
       # ...


Job persistence
---------------

Submitted cloud jobs and single-circuit direct-access jobs can be persisted and
restored across processes. See :doc:`persistence` for the storage API and the
direct-access composite-job limitation.


Qiskit primitives
-----------------

There have been significant changes to the Sampler and Estimator primitive APIs. Check the `Qiskit primitives migration guide <https://quantum.cloud.ibm.com/docs/en/guides/v2-primitives>`_ for more information on how to update your code if you use these.


Qiskit
------

The v2 provider supports Python 3.10–3.14 and Qiskit 2.3–2.4.1. See the `Qiskit 2.0 migration guide <https://quantum.cloud.ibm.com/docs/en/guides/qiskit-2.0>`_ for more details on how to update your non-provider code.
