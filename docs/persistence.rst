###############
Job persistence
###############

Remote jobs can outlive the Python process that submitted them. Persist a
submitted cloud or single-circuit direct-access job, then restore it later with
a newly configured backend:

.. code-block:: python

   from qiskit_aqt_provider import AQTProvider
   from qiskit_aqt_provider.persistence import FileJobStore

   store = FileJobStore()

   with AQTProvider() as provider:
       backend = provider.cloud().fetch_workspaces().get_by_id("workspace").get_backend("resource")
       job = backend.run(circuit, shots=100, memory=True)
       job.persist(store=store)
       job_id = job.job_id()

   # In a later process, authenticate and acquire the same backend again.
   with AQTProvider() as provider:
       backend = provider.cloud().fetch_workspaces().get_by_id("workspace").get_backend("resource")
       job = backend.restore_job(job_id, store=store)
       result = job.result()

``FileJobStore()`` uses a stable platform-specific user-data directory. Pass a
directory to ``FileJobStore(path)`` for an explicit location, or implement the
``JobStore`` protocol to use another storage system. Persisted files contain
the circuits and execution options, but never credentials or network clients;
protect or delete them when circuit data is sensitive.

Records remain available after restoration by default. Pass ``delete=True`` to
``restore_job`` to remove the record after it has been successfully decoded and
reconstructed. Deletion is also available through the store's ``delete``
method.

For direct access, acquire the resource again with the same endpoint and token,
then call the same ``restore_job`` method:

.. code-block:: python

   with AQTProvider() as provider:
       backend = provider.direct_access().get_resource(base_url, access_token)
       job = backend.restore_job(job_id, store=store)
       result = job.result()

Direct-access backends support persistence for a single circuit. Their current
multi-circuit jobs are lazy composites that submit circuits one at a time while
``result()`` runs, so those composite handles cannot be persisted. If you want
to persist multiple circuits, create separate single-circuit direct-access jobs
for each one.
