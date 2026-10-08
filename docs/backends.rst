.. _backends:

==============
AQT Backends
==============

Usage
=====

Handles to computing resources are obtained through the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class.

You can use the provider to access AQT resources:

- using the :ref:`AQT Arnica cloud portal<cloud-usage>`
- using :ref:`offline simulators<offline-usage>`
- using :ref:`direct access<direct-usage>`

Selecting a backend at runtime
------------------------------

Applications can select one backend at runtime and use it for the entire
script. For example, run the script with ``AQT_PROVIDER=offline`` to test a
circuit locally, then set it to ``direct`` or ``cloud`` and run the script
again. The resulting backend handle can be used the same way in each case:

.. code-block:: python

   import os

   from qiskit_aqt_provider import AQTProvider

   provider_type = os.getenv("AQT_PROVIDER", "offline")

   def get_backend(provider: AQTProvider, provider_type: str):
      if provider_type == "offline":
         return provider.offline.ideal()

      if provider_type == "direct":
         return provider.direct_access().get_resource(
            os.environ["AQT_DIRECT_URL"],
            os.environ["AQT_TOKEN"],
         )

      if provider_type == "cloud":
         workspaces = provider.cloud().fetch_workspaces()
         workspace = workspaces.get_by_id(os.environ["AQT_WORKSPACE_ID"])
         return workspace.get_backend(os.environ["AQT_RESOURCE_ID"])

      raise ValueError(f"Unknown provider: {provider_type}")

   with AQTProvider() as provider:
      backend = get_backend(provider, provider_type)
      result = backend.run(circuit).result()

For cloud access, authenticate first as described in the :ref:`cloud`
authentication guide. ``AQT_PROVIDER`` accepts ``offline``, ``cloud``, or
``direct`` and defaults to ``offline``.


.. toctree::
  :maxdepth: 1
  :hidden:

  Cloud access <cloud>
  Offline simulators <offline>
  Direct access <direct>
