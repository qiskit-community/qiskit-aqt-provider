.. _cloud:

=======================
AQT Arnica cloud portal
=======================

This guide covers usage of the Qiskit AQT provider package with the AQT Arnica cloud portal.

.. _cloud-usage:

Usage
=====

The recommended way to use the :class:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider>` class to access AQT Arnica cloud resources is as a context manager. This will ensure that connections are properly cleaned up when leaving the context.

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider

   with AQTProvider() as provider:
      cloud = provider.cloud()
      ...


Authentication
==============

Using an Arnica account
-------------------------------------
.. tip:: Use this method if you were asked to create your own account to use the AQT Arnica portal.

Call :meth:`log_in <qiskit_aqt_provider._cloud.provider.CloudProvider.log_in>` to start the authentication flow and store your access token securely on the local machine.

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider

   with AQTProvider() as provider:
      cloud = provider.cloud()
      cloud.log_in()

.. hint:: The access token has an expiration time of 10 hours. After this time, you'll need to call the `log_in` method again to refresh your token. You shouldn't need to enter your password again unless you last logged in a very long time ago. You can safely call `log_in` at any time, as nothing will happen if your access token is still valid.

Using client credentials
------------------------
.. tip:: Use this method if you received client credentials from AQT to use the Arnica portal.

Pass an instance of the `ArnicaConfig` helper class to :meth:`AQTProvider <qiskit_aqt_provider.aqt_provider.AQTProvider.cloud>`, then call :meth:`log_in <qiskit_aqt_provider._cloud.provider.CloudProvider.log_in>` to exchange your credentials for an access token, which is stored on the local machine.

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider
   from qiskit_aqt_provider.aqt_provider import ArnicaConfig

   config = ArnicaConfig(
       client_id="YOUR_CLIENT_ID",
       client_secret="YOUR_CLIENT_SECRET",
   )
   with AQTProvider() as provider:
      cloud = provider.cloud(config)
      cloud.log_in()


Using a static API token (deprecated)
--------------------------------------
.. versionremoved:: 2.0.0

   Static API tokens are no longer supported. If you've only received a static access token from AQT, you can contact AQT support to get an account.


Listing accessible resources
============================

Cloud resources can be accessed through a *workspace*. Each workspace may contain multiple *resources*, which can be of different *types* (``device`` or ``simulator``).

To see which workspaces you have access to, call the :meth:`fetch_workspaces <qiskit_aqt_provider._cloud.provider.CloudProvider.fetch_workspaces>` method on the cloud handle:

.. code-block:: python

    ...
    all_workspaces = cloud.fetch_workspaces()
    for workspace in all_workspaces:
        print(workspace.id)

.. hint:: You should have received the ID of the workspace(s) you have access to from AQT. If you're not sure which to use, please contact AQT support.

Get a provider for a single workspace by passing its ID to the :meth:`get_by_id <qiskit_aqt_provider._cloud.workspace_collection.WorkspaceCollection.get_by_id>` method on the workspaces handle:

.. code-block:: python

    workspace = all_workspaces.get_by_id("my_workspace_id")

Then list the backends available in that workspace by calling the :meth:`list_backends <qiskit_aqt_provider._cloud.workspace_provider.WorkspaceProvider.list_backends>` method on the workspace handle:

.. code-block:: python

    ...
    backends = workspace.list_backends()
    for backend in backends:
        print(backend.id, backend.type)


And finally get a handle to a specific backend by passing its ID to the :meth:`get_backend <qiskit_aqt_provider._cloud.workspace_provider.WorkspaceProvider.get_backend>` method on the workspace handle:

.. code-block:: python

    ...
    backend = workspace.get_backend("my_backend_id")

If no backend with the given ID is found, a :class:`QiskitBackendNotFoundError <qiskit.providers.QiskitBackendNotFoundError>` exception is raised.


Quantum register size
=====================

The number of qubits available on a given resource may vary. This is because the number of ions loaded in an AQT quantum computing resource is adjustable. All-to-all connectivity is always guaranteed, independently of the number of available qubits.

The number of qubits available for cloud resources cannot be configured with this provider. 

.. warning:: The number of qubits is fetched from the API when initializing the resource handle, i.e. when calling :meth:`get_backend <qiskit_aqt_provider._cloud.workspace_provider.WorkspaceProvider.get_backend>`. Subsequent transpilation calls will assume that at least this number of qubits is available.
