from qiskit import QuantumCircuit, transpile

from qiskit_aqt_provider.aqt_provider import AQTProvider

# If no `access_token` is passed to the constructor it is read from
# the AQT_TOKEN environment variable
provider = AQTProvider("")

# The workspaces method returns a list of available workspaces and resources
print(provider.workspaces())

# Retrieve a backend by providing a `workspace` and `device_id`
backend = provider.get_resource("aqt", "simulator_no_noise")

# Creating and running a circuit works as before:
qc = QuantumCircuit(4, 4)
qc.h(0)
qc.cx(0, 1)
qc.cx(0, 2)
qc.cx(0, 3)
qc.measure([0, 1, 2, 3], [0, 1, 2, 3])
trans_qc = transpile(qc, backend, optimization_level=3)
job = backend.run(trans_qc, shots=200)
print(job.result().get_counts())
